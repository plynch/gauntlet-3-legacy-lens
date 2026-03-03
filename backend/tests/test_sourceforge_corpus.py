import subprocess
from pathlib import Path

import pytest

from app.services.sourceforge_corpus import count_corpus, run_svn_export


def test_run_svn_export_raises_on_missing_binary(monkeypatch, tmp_path) -> None:
    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="requires `svn`"):
        run_svn_export(Path(tmp_path / "trunk"), timeout_seconds=10)


def test_run_svn_export_surfaces_command_failure(monkeypatch, tmp_path) -> None:
    def fake_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="svn", stderr="fatal: network error")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="fatal: network error"):
        run_svn_export(Path(tmp_path / "trunk"), timeout_seconds=10)


def test_count_corpus_counts_all_files(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.cob").write_text("LINE 1\nLINE 2\n", encoding="utf-8")
    (corpus / "b.cpy").write_text("COPY 1\n", encoding="utf-8")
    (corpus / "readme.txt").write_text("nope\n", encoding="utf-8")

    files, loc, bytes_total = count_corpus(corpus)

    assert files == 3
    assert loc == 4
    assert bytes_total > 0
