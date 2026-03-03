import hashlib
import math
from collections.abc import Sequence

import httpx

from app.services.types import SearchHit


class OpenAIGateway:
    def __init__(self, api_key: str | None, timeout_seconds: float = 45.0, local_embedding_dimensions: int = 256):
        self._api_key = api_key
        self._local_embedding_dimensions = local_embedding_dimensions
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def embed_texts(self, texts: Sequence[str], model: str) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            return [local_embedding(text, self._local_embedding_dimensions) for text in texts]

        response = self._client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={"model": model, "input": list(texts)},
        )
        if not response.is_success:
            raise RuntimeError(f"Failed to embed texts: {response.status_code} {response.text}")

        data = response.json()
        return [item["embedding"] for item in data.get("data", [])]

    def generate_answer(self, question: str, hits: Sequence[SearchHit], model: str, max_context_characters: int) -> str:
        if not hits:
            return "I could not find enough evidence in the indexed corpus to answer this question."
        if not self._api_key:
            return fallback_answer(question, hits)

        context = build_context(hits, max_context_characters=max_context_characters)
        system_prompt = (
            "You answer questions about a codebase using only provided evidence. "
            "If evidence is insufficient, clearly say so. "
            "Keep the answer concise and include citations in format [path:start-end]."
        )
        user_prompt = f"Question:\n{question}\n\nEvidence:\n{context}"

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
        if not response.is_success:
            return fallback_answer(question, hits)

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return fallback_answer(question, hits)
        return choices[0].get("message", {}).get("content", "").strip() or fallback_answer(question, hits)


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
