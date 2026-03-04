import hashlib
import math
import time
from collections.abc import Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

import httpx

from app.services.openai_resilience import (
    OpenAIModeStatus,
    describe_openai_mode,
    get_generation_circuit_snapshot,
    record_generation_failure,
    record_generation_success,
)
from app.services.types import SearchHit

if TYPE_CHECKING:
    from app.services.tracing import LangfuseTracer


class OpenAIGateway:
    def __init__(
        self,
        api_key: str | None,
        timeout_seconds: float = 120.0,
        local_embedding_dimensions: int = 256,
        embedding_max_retries: int = 3,
        embedding_retry_backoff_seconds: float = 1.5,
        generation_circuit_failure_threshold: int = 3,
        generation_circuit_cooldown_seconds: float = 90.0,
        tracer: "LangfuseTracer | None" = None,
    ):
        self._api_key = api_key
        self._local_embedding_dimensions = local_embedding_dimensions
        self._embedding_max_retries = max(1, embedding_max_retries)
        self._embedding_retry_backoff_seconds = max(0.1, embedding_retry_backoff_seconds)
        self._generation_circuit_failure_threshold = max(1, generation_circuit_failure_threshold)
        self._generation_circuit_cooldown_seconds = max(1.0, generation_circuit_cooldown_seconds)
        self._client = httpx.Client(timeout=timeout_seconds)
        self._tracer = tracer

    @property
    def tracer(self) -> "LangfuseTracer | None":
        return self._tracer

    def close(self) -> None:
        self._client.close()

    def mode_status(self) -> OpenAIModeStatus:
        return describe_openai_mode(
            api_key=self._api_key,
            generation_circuit_snapshot=get_generation_circuit_snapshot(),
        )

    def embed_texts(self, texts: Sequence[str], model: str) -> list[list[float]]:
        if not texts:
            return []
        with self._generation_trace(
            name="openai.embeddings",
            model=model,
            input={
                "text_count": len(texts),
                "total_characters": sum(len(text) for text in texts),
            },
            metadata={"provider": "openai", "uses_remote_model": bool(self._api_key)},
        ) as trace:
            if not self._api_key:
                vectors = [local_embedding(text, self._local_embedding_dimensions) for text in texts]
                trace.update(output={"vector_count": len(vectors), "mode": "local-fallback"})
                return vectors

            last_error: RuntimeError | None = None
            for attempt in range(1, self._embedding_max_retries + 1):
                try:
                    response = self._client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        json={"model": model, "input": list(texts)},
                    )
                except httpx.TimeoutException as exc:
                    last_error = RuntimeError(f"Embedding request timed out on attempt {attempt}.")
                    trace.update(metadata={"attempt": attempt, "status": "timeout"})
                    if attempt < self._embedding_max_retries:
                        self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc
                except httpx.RequestError as exc:
                    last_error = RuntimeError(f"Embedding request failed on attempt {attempt}: {exc}")
                    trace.update(metadata={"attempt": attempt, "status": "request_error"})
                    if attempt < self._embedding_max_retries:
                        self._sleep_before_retry(attempt)
                        continue
                    raise last_error from exc

                if response.is_success:
                    data = response.json()
                    vectors = [item["embedding"] for item in data.get("data", [])]
                    trace.update(
                        output={
                            "vector_count": len(vectors),
                            "mode": "openai",
                            "attempt": attempt,
                        }
                    )
                    return vectors

                if response.status_code in {408, 409, 429} or response.status_code >= 500:
                    last_error = RuntimeError(
                        f"Embedding request returned retriable status {response.status_code} on attempt {attempt}."
                    )
                    trace.update(metadata={"attempt": attempt, "status_code": response.status_code, "status": "retryable_http_error"})
                    if attempt < self._embedding_max_retries:
                        self._sleep_before_retry(attempt)
                        continue

                raise RuntimeError(f"Failed to embed texts: {response.status_code} {response.text}")

            raise last_error or RuntimeError("Failed to embed texts after retries.")

    def generate_answer(self, question: str, hits: Sequence[SearchHit], model: str, max_context_characters: int) -> str:
        with self._generation_trace(
            name="openai.chat_completion",
            model=model,
            input={
                "question": question,
                "hit_count": len(hits),
                "top_citations": [f"{hit.source_path}:{hit.line_start}-{hit.line_end}" for hit in hits[:3]],
            },
            metadata={"provider": "openai", "uses_remote_model": bool(self._api_key)},
            model_parameters={"temperature": 0.1},
        ) as trace:
            if not hits:
                answer = "I could not find enough evidence in the indexed corpus to answer this question."
                trace.update(output={"mode": "no_hits", "answer_preview": answer[:500]})
                return answer
            if not self._api_key:
                answer = fallback_answer(question, hits)
                trace.update(output={"mode": "local-fallback", "answer_preview": answer[:500]})
                return answer

            circuit_snapshot = get_generation_circuit_snapshot()
            if circuit_snapshot.is_open:
                answer = fallback_answer(question, hits)
                trace.update(
                    output={
                        "mode": "fallback_circuit_open",
                        "answer_preview": answer[:500],
                        "seconds_until_retry": circuit_snapshot.seconds_remaining,
                        "last_error": circuit_snapshot.last_error,
                    }
                )
                return answer

            context = build_context(hits, max_context_characters=max_context_characters)
            system_prompt = (
                "You answer questions about a codebase using only provided evidence. "
                "If evidence is insufficient, clearly say so. "
                "Keep the answer concise and include citations in format [path:start-end]."
            )
            user_prompt = f"Question:\n{question}\n\nEvidence:\n{context}"

            try:
                response = self._client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "temperature": 0.1,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                record_generation_failure(
                    error=str(exc),
                    threshold=self._generation_circuit_failure_threshold,
                    cooldown_seconds=self._generation_circuit_cooldown_seconds,
                )
                answer = fallback_answer(question, hits)
                trace.update(output={"mode": "fallback_transport_error", "answer_preview": answer[:500], "error": str(exc)})
                return answer

            if not response.is_success:
                record_generation_failure(
                    error=f"{response.status_code} {response.text[:200]}",
                    threshold=self._generation_circuit_failure_threshold,
                    cooldown_seconds=self._generation_circuit_cooldown_seconds,
                )
                answer = fallback_answer(question, hits)
                trace.update(
                    output={
                        "mode": "fallback_http_error",
                        "status_code": response.status_code,
                        "answer_preview": answer[:500],
                    }
                )
                return answer

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                record_generation_failure(
                    error="empty choices",
                    threshold=self._generation_circuit_failure_threshold,
                    cooldown_seconds=self._generation_circuit_cooldown_seconds,
                )
                answer = fallback_answer(question, hits)
                trace.update(output={"mode": "fallback_empty_choices", "answer_preview": answer[:500]})
                return answer
            answer = choices[0].get("message", {}).get("content", "").strip() or fallback_answer(question, hits)
            record_generation_success()
            trace.update(output={"mode": "openai", "answer_preview": answer[:500], "choice_count": len(choices)})
            return answer

    def _sleep_before_retry(self, attempt: int) -> None:
        backoff_seconds = self._embedding_retry_backoff_seconds * (2 ** (attempt - 1))
        time.sleep(backoff_seconds)

    @contextmanager
    def _generation_trace(
        self,
        *,
        name: str,
        model: str,
        input: dict[str, object],
        metadata: dict[str, object] | None = None,
        model_parameters: dict[str, object] | None = None,
    ):
        if not self._tracer:
            yield _NullTrace()
            return
        with self._tracer.generation(
            name=name,
            model=model,
            input=input,
            metadata=metadata,
            model_parameters=model_parameters,
        ) as trace:
            yield trace


class _NullTrace:
    def update(self, **kwargs: object) -> None:  # pragma: no cover - trivial no-op
        return


def build_context(hits: Sequence[SearchHit], max_context_characters: int) -> str:
    chunks: list[str] = []
    total = 0
    for hit in hits:
        citation = f"[{hit.source_path}:{hit.line_start}-{hit.line_end}]"
        segment = f"{citation}\n{hit.text}\n"
        if total + len(segment) > max_context_characters and chunks:
            break
        chunks.append(segment)
        total += len(segment)
    return "\n".join(chunks)


def fallback_answer(question: str, hits: Sequence[SearchHit]) -> str:
    top_hit = hits[0]
    top_citation = f"[{top_hit.source_path}:{top_hit.line_start}-{top_hit.line_end}]"
    related = ", ".join(
        f"[{hit.source_path}:{hit.line_start}-{hit.line_end}]"
        for hit in hits[1:3]
    )
    related_text = f" Related evidence: {related}." if related else ""
    return (
        f"Using available evidence, the strongest match for '{question}' is {top_citation}.{related_text} "
        "Configure LEGACYLENS_OPENAI_API_KEY for model-generated synthesis."
    )


def local_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0 for _ in range(dimensions)]
    if not text:
        return vector

    for token in tokenize(text):
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def tokenize(text: str) -> list[str]:
    return [part for part in text.lower().replace("\n", " ").split(" ") if part]
