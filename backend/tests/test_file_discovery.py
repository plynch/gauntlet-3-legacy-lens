from pathlib import Path

from app.services.file_discovery import discover_source_files, normalize_extension, read_text_safely


def test_discover_source_files_filters_extensions(tmp_path: Path) -> None:
    source_dir = tmp_path / "corpus"
    source_dir.mkdir()
    (source_dir / "a.cbl").write_text("A", encoding="utf-8")
    (source_dir / "b.COB").write_text("B", encoding="utf-8")
    (source_dir / "readme.txt").write_text("skip", encoding="utf-8")

    files = discover_source_files([str(source_dir)], [".cbl", ".cob"])
    paths = [path.name for path in files]

    assert paths == ["a.cbl", "b.COB"]


def test_normalize_extension_handles_missing_dot() -> None:
    assert normalize_extension("cbl") == ".cbl"
    assert normalize_extension(".cob") == ".cob"


def test_read_text_safely_falls_back_to_replacement(tmp_path: Path) -> None:
    path = tmp_path / "latin1.cbl"
    path.write_bytes("caf\xe9".encode("latin-1"))

    content = read_text_safely(path)

    assert "caf" in content
