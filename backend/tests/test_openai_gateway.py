from app.services.openai_gateway import (
    OpenAIGateway,
    build_context,
    local_embedding,
)
from app.services.openai_resilience import describe_openai_mode, reset_generation_circuit_for_tests
from app.services.types import SearchHit


def test_local_embedding_is_deterministic() -> None:
    first = local_embedding("READ CUSTOMER FILE", dimensions=32)
    second = local_embedding("READ CUSTOMER FILE", dimensions=32)

    assert first == second
    assert len(first) == 32


def test_build_context_respects_character_budget() -> None:
    hits = [
        SearchHit(
            text="A" * 200,
            score=0.8,
            source_path="a.cbl",
            line_start=1,
            line_end=10,
            section="A",
        ),
        SearchHit(
            text="B" * 200,
            score=0.7,
            source_path="b.cbl",
            line_start=11,
            line_end=20,
            section="B",
        ),
    ]

    context = build_context(hits, max_context_characters=250)

    assert "[a.cbl:1-10]" in context
    assert "[b.cbl:11-20]" not in context


def test_gateway_uses_fallback_answer_without_api_key() -> None:
    reset_generation_circuit_for_tests()
    gateway = OpenAIGateway(api_key=None, local_embedding_dimensions=16)
    hits = [
        SearchHit(
            text="OPEN INPUT CUSTOMER-FILE",
            score=0.9,
            source_path="data/corpus/customer_accounts.cbl",
            line_start=35,
            line_end=37,
            section="OPEN-FILES",
        )
    ]

    answer = gateway.generate_answer(
        question="Where is file opened?",
        hits=hits,
        model="gpt-4.1-mini",
        max_context_characters=1000,
    )

    assert "strongest match" in answer
    assert "customer_accounts.cbl:35-37" in answer
    gateway.close()


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload: dict | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict:
        return self._payload


class FailingClient:
    def __init__(self) -> None:
        self.calls = 0

    def post(self, *args, **kwargs) -> FakeResponse:  # type: ignore[no-untyped-def]
        del args, kwargs
        self.calls += 1
        return FakeResponse(status_code=500, text="upstream unavailable")

    def close(self) -> None:
        return


def test_generation_circuit_breaker_opens_after_repeated_failures() -> None:
    reset_generation_circuit_for_tests()
    gateway = OpenAIGateway(
        api_key="test-key",
        generation_circuit_failure_threshold=2,
        generation_circuit_cooldown_seconds=60.0,
    )
    failing_client = FailingClient()
    gateway._client = failing_client  # type: ignore[assignment]
    hits = [
        SearchHit(
            text="MOVE 1 TO COUNT",
            score=0.91,
            source_path="sample.cbl",
            line_start=10,
            line_end=15,
            section="COUNTING",
        )
    ]

    first = gateway.generate_answer(
        question="Where is counting logic?",
        hits=hits,
        model="gpt-4.1-mini",
        max_context_characters=8000,
    )
    second = gateway.generate_answer(
        question="Where is counting logic?",
        hits=hits,
        model="gpt-4.1-mini",
        max_context_characters=8000,
    )
    third = gateway.generate_answer(
        question="Where is counting logic?",
        hits=hits,
        model="gpt-4.1-mini",
        max_context_characters=8000,
    )

    assert "strongest match" in first
    assert "strongest match" in second
    assert "strongest match" in third
    assert failing_client.calls == 2  # Third request is short-circuited by the circuit breaker.

    mode = describe_openai_mode(api_key="test-key")
    assert mode.mode == "fallback"
    assert mode.degraded_reason is not None
    assert "circuit breaker is open" in mode.degraded_reason.lower()
    gateway.close()
