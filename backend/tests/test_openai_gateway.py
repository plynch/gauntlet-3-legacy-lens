from app.services.openai_gateway import OpenAIGateway, build_context, local_embedding
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
