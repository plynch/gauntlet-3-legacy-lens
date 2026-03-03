from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

try:
    try:
        from langfuse import Langfuse as LangfuseClient
    except ImportError:
        from langfuse.otel import Langfuse as LangfuseClient
except Exception:  # pragma: no cover - defensive import fallback
    LangfuseClient = None


class TraceObservation:
    def __init__(self, observation: Any | None):
        self._observation = observation

    def update(self, **kwargs: Any) -> None:
        if not self._observation:
            return
        updater = getattr(self._observation, "update", None)
        if not callable(updater):
            return
        try:
            updater(**kwargs)
        except Exception:
            # Observability must never block the request path.
            return

    def score(self, **kwargs: Any) -> None:
        if not self._observation:
            return
        scorer = getattr(self._observation, "score", None)
        if not callable(scorer):
            return
        try:
            scorer(**kwargs)
        except Exception:
            return


class LangfuseTracer:
    def __init__(
        self,
        *,
        base_url: str | None,
        public_key: str | None,
        secret_key: str | None,
        environment: str,
    ) -> None:
        self._environment = environment
        self._client: Any | None = None
        if not (LangfuseClient and public_key and secret_key):
            return
        try:
            kwargs: dict[str, Any] = {
                "public_key": public_key,
                "secret_key": secret_key,
            }
            if base_url:
                kwargs["host"] = base_url
            self._client = LangfuseClient(**kwargs)
        except Exception:
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @contextmanager
    def span(
        self,
        *,
        name: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[TraceObservation]:
        context_manager = self._start_observation_context(
            method_name="start_as_current_span",
            name=name,
            input=input,
            metadata=self._with_environment(metadata),
        )
        if context_manager is None:
            yield TraceObservation(None)
            return
        with self._enter_context_manager(context_manager) as observation:
            yield observation

    @contextmanager
    def generation(
        self,
        *,
        name: str,
        model: str,
        input: Any | None = None,
        metadata: dict[str, Any] | None = None,
        model_parameters: dict[str, Any] | None = None,
    ) -> Iterator[TraceObservation]:
        context_manager = self._start_observation_context(
            method_name="start_as_current_generation",
            name=name,
            model=model,
            input=input,
            metadata=self._with_environment(metadata),
            model_parameters=model_parameters,
        )
        if context_manager is None:
            with self.span(name=name, input=input, metadata={"model": model, **(metadata or {})}) as span_observation:
                yield span_observation
            return
        with self._enter_context_manager(context_manager) as observation:
            yield observation

    def flush(self) -> None:
        if not self._client:
            return
        flusher = getattr(self._client, "flush", None)
        if not callable(flusher):
            return
        try:
            flusher()
        except Exception:
            return

    def close(self) -> None:
        self.flush()
        if not self._client:
            return
        shutdown = getattr(self._client, "shutdown", None)
        if not callable(shutdown):
            return
        try:
            shutdown()
        except Exception:
            return

    def _with_environment(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(metadata or {})
        merged.setdefault("environment", self._environment)
        return merged

    def _start_observation_context(self, method_name: str, **kwargs: Any) -> Any | None:
        if not self._client:
            return None
        starter = getattr(self._client, method_name, None)
        if not callable(starter):
            return None
        try:
            return starter(**kwargs)
        except TypeError:
            try:
                fallback_kwargs: dict[str, Any] = {"name": kwargs["name"]}
                if "input" in kwargs:
                    fallback_kwargs["input"] = kwargs["input"]
                if "metadata" in kwargs:
                    fallback_kwargs["metadata"] = kwargs["metadata"]
                if "model" in kwargs:
                    fallback_kwargs["model"] = kwargs["model"]
                return starter(**fallback_kwargs)
            except Exception:
                return None
        except Exception:
            return None

    @contextmanager
    def _enter_context_manager(self, context_manager: Any) -> Iterator[TraceObservation]:
        try:
            observation = context_manager.__enter__()
        except Exception:
            yield TraceObservation(None)
            return

        wrapped = TraceObservation(observation)
        try:
            yield wrapped
        except Exception as exc:
            context_manager.__exit__(type(exc), exc, exc.__traceback__)
            raise
        else:
            context_manager.__exit__(None, None, None)
