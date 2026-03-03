from app.services.cobol_chunker import chunk_cobol_source
from app.services.types import SourceFile


def test_chunk_cobol_source_emits_metadata() -> None:
    text = "\n".join(
        [
            "       PROCEDURE DIVISION.",
            "       MAIN-LOGIC.",
            "           PERFORM READ-CUSTOMER.",
            "       READ-CUSTOMER.",
            "           READ CUSTOMER-FILE.",
        ]
    )
    source = SourceFile(path="sample.cbl", text=text, sha1="abc123")

    chunks = chunk_cobol_source(source, max_lines=10, overlap_lines=2)

    assert len(chunks) >= 1
    first = chunks[0]
    assert first.source_path == "sample.cbl"
    assert first.line_start >= 1
    assert first.line_end >= first.line_start
    assert first.file_hash == "abc123"
