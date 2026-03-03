import re
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from app.models.corpus import SourceForgeSyncStats

SOURCEFORGE_TREE_URL = "https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/"
SOURCEFORGE_TARBALL_URL = "https://sourceforge.net/p/gnucobol/code/HEAD/tarball"
TOKEN_PATTERN = r'name="_csrf_token" type="hidden" value="([^"]+)"'
CORPUS_SUFFIXES = (".cbl", ".cob", ".cpy", ".copy")


def sync_sourceforge_trunk(destination_path: str, timeout_seconds: int = 120) -> SourceForgeSyncStats:
    destination = Path(destination_path)
    destination.mkdir(parents=True, exist_ok=True)

    opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor())
    tree_html = http_read_text(opener, SOURCEFORGE_TREE_URL, timeout_seconds)
    token = extract_csrf_token(tree_html)

    payload = urllib_parse.urlencode({"path": "/trunk", "_csrf_token": token}).encode("utf-8")
    snapshot_bytes = http_post_bytes(opener, SOURCEFORGE_TARBALL_URL, payload, timeout_seconds)

    with tempfile.TemporaryDirectory(prefix="legacylens-sourceforge-") as temp_dir:
        temp_root = Path(temp_dir)
        archive_path = temp_root / "sourceforge-trunk.tar.gz"
        extract_path = temp_root / "extract"
        archive_path.write_bytes(snapshot_bytes)
        extract_path.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, mode="r:gz") as tar:
            tar.extractall(path=extract_path)

        root_entries = [entry for entry in extract_path.iterdir() if entry.is_dir()]
        if not root_entries:
            raise RuntimeError("SourceForge snapshot extraction produced no directory content.")

        extracted_root = root_entries[0]
        clear_directory(destination)
        copy_tree(extracted_root, destination)

    files_synced, corpus_loc, corpus_bytes = count_corpus(destination)
    return SourceForgeSyncStats(
        source_url=SOURCEFORGE_TREE_URL,
        destination_path=str(destination),
        synced_at=datetime.now(timezone.utc),
        files_synced=files_synced,
        corpus_loc=corpus_loc,
        corpus_bytes=corpus_bytes,
    )


def http_read_text(opener: urllib_request.OpenerDirector, url: str, timeout_seconds: int) -> str:
    with opener.open(url, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def http_post_bytes(
    opener: urllib_request.OpenerDirector, url: str, payload: bytes, timeout_seconds: int
) -> bytes:
    request = urllib_request.Request(url=url, data=payload, method="POST")
    with opener.open(request, timeout=timeout_seconds) as response:
        return response.read()


def extract_csrf_token(html: str) -> str:
    match = re.search(TOKEN_PATTERN, html)
    if not match:
        raise RuntimeError("Failed to parse SourceForge CSRF token.")
    return match.group(1)


def clear_directory(path: Path) -> None:
    for entry in path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def copy_tree(source: Path, destination: Path) -> None:
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)


def count_corpus(directory: Path) -> tuple[int, int, int]:
    files = [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in CORPUS_SUFFIXES]
    total_lines = 0
    total_bytes = 0

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        total_lines += len(content.splitlines())
        total_bytes += len(content.encode("utf-8", errors="ignore"))

    return len(files), total_lines, total_bytes
