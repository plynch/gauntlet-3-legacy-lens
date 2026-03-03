import pytest

from app.services.sourceforge_corpus import count_corpus, extract_csrf_token


def test_extract_csrf_token_parses_hidden_input() -> None:
    html = '<input name="_csrf_token" type="hidden" value="abc123token">'
    assert extract_csrf_token(html) == "abc123token"


def test_extract_csrf_token_raises_on_missing_token() -> None:
    with pytest.raises(RuntimeError):
        extract_csrf_token("<html></html>")


def test_count_corpus_counts_only_supported_extensions(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.cob").write_text("LINE 1\nLINE 2\n", encoding="utf-8")
    (corpus / "b.cpy").write_text("COPY 1\n", encoding="utf-8")
    (corpus / "skip.txt").write_text("nope\n", encoding="utf-8")

    files, loc, bytes_total = count_corpus(corpus)

    assert files == 2
    assert loc == 3
    assert bytes_total > 0
