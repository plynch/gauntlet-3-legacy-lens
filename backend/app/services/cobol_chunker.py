import re
import uuid

from app.services.types import SourceChunk, SourceFile

SECTION_PATTERN = re.compile(r"^\s{0,7}([A-Za-z0-9-]+)\.\s*$")


def chunk_cobol_source(source: SourceFile, max_lines: int, overlap_lines: int) -> list[SourceChunk]:
    lines = source.text.splitlines()
    if not lines:
        return []

    segments = find_segments(lines)
    chunks: list[SourceChunk] = []

    for segment_start, segment_end, section in segments:
        chunks.extend(
            chunk_segment(
                source=source,
                lines=lines,
                start=segment_start,
                end=segment_end,
                section=section,
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        )

    return chunks


def find_segments(lines: list[str]) -> list[tuple[int, int, str | None]]:
    anchors: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        matched = SECTION_PATTERN.match(line)
        if matched:
            anchors.append((index, matched.group(1)))

    if not anchors:
        return [(0, len(lines), None)]

    segments: list[tuple[int, int, str | None]] = []
    for idx, (start, section) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else len(lines)
        segments.append((start, end, section))
    return segments


def chunk_segment(
    source: SourceFile,
    lines: list[str],
    start: int,
    end: int,
    section: str | None,
    max_lines: int,
    overlap_lines: int,
) -> list[SourceChunk]:
    if end - start <= max_lines:
        text = "\n".join(lines[start:end]).strip()
        return [build_chunk(source, text, start + 1, end, section)] if text else []

    chunks: list[SourceChunk] = []
    step = max(1, max_lines - overlap_lines)
    window_start = start

    while window_start < end:
        window_end = min(end, window_start + max_lines)
        text = "\n".join(lines[window_start:window_end]).strip()
        if text:
            chunks.append(build_chunk(source, text, window_start + 1, window_end, section))
        if window_end >= end:
            break
        window_start += step

    return chunks


def build_chunk(
    source: SourceFile,
    text: str,
    line_start: int,
    line_end: int,
    section: str | None,
) -> SourceChunk:
    raw_id = f"{source.path}:{line_start}:{line_end}:{source.sha1}"
    chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, raw_id))
    return SourceChunk(
        id=chunk_id,
        text=text,
        source_path=source.path,
        file_hash=source.sha1,
        line_start=line_start,
        line_end=line_end,
        section=section,
    )
