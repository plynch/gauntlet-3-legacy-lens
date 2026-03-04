import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class OpenAIModeStatus:
    mode: str
    degraded_reason: str | None


@dataclass(frozen=True)
class GenerationCircuitSnapshot:
    is_open: bool
    seconds_remaining: int
    last_error: str | None


class GenerationCircuitState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._open_until_monotonic = 0.0
        self._failure_count = 0
        self._last_error: str | None = None

    def snapshot(self) -> GenerationCircuitSnapshot:
        with self._lock:
            seconds_remaining = max(0, int(round(self._open_until_monotonic - time.monotonic())))
            return GenerationCircuitSnapshot(
                is_open=seconds_remaining > 0,
                seconds_remaining=seconds_remaining,
                last_error=self._last_error,
            )

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._open_until_monotonic = 0.0
            self._last_error = None

    def record_failure(self, error: str, threshold: int, cooldown_seconds: float) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_error = error
            if self._failure_count >= threshold:
                self._open_until_monotonic = time.monotonic() + cooldown_seconds
                self._failure_count = 0

    def reset(self) -> None:
        with self._lock:
            self._open_until_monotonic = 0.0
            self._failure_count = 0
            self._last_error = None


_GENERATION_CIRCUIT = GenerationCircuitState()


def get_generation_circuit_snapshot() -> GenerationCircuitSnapshot:
    return _GENERATION_CIRCUIT.snapshot()


def record_generation_success() -> None:
    _GENERATION_CIRCUIT.record_success()


def record_generation_failure(error: str, threshold: int, cooldown_seconds: float) -> None:
    _GENERATION_CIRCUIT.record_failure(error, threshold=threshold, cooldown_seconds=cooldown_seconds)


def describe_openai_mode(
    api_key: str | None,
    generation_circuit_snapshot: GenerationCircuitSnapshot | None = None,
) -> OpenAIModeStatus:
    if not api_key:
        return OpenAIModeStatus(mode="fallback", degraded_reason="OpenAI API key is not configured.")

    snapshot = generation_circuit_snapshot or get_generation_circuit_snapshot()
    if snapshot.is_open:
        reason = f"OpenAI generation circuit breaker is open ({snapshot.seconds_remaining}s until retry)."
        return OpenAIModeStatus(mode="fallback", degraded_reason=reason)
    return OpenAIModeStatus(mode="openai", degraded_reason=None)


def reset_generation_circuit_for_tests() -> None:
    _GENERATION_CIRCUIT.reset()
