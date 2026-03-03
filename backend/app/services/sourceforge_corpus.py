import subprocess
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.corpus import SourceForgeSyncStats

SOURCEFORGE_TREE_URL = "https://sourceforge.net/p/gnucobol/code/HEAD/tree/trunk/"
SOURCEFORGE_SVN_TRUNK_URL = "https://svn.code.sf.net/p/gnucobol/code/trunk"


def sync_sourceforge_trunk(destination_path: str, timeout_seconds: int = 120) -> SourceForgeSyncStats:
    destination = Path(destination_path)
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="legacylens-sourceforge-") as temp_dir:
        temp_root = Path(temp_dir)
        extracted_root = temp_root / "trunk"
        run_svn_export(extracted_root, timeout_seconds=timeout_seconds)
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


def run_svn_export(destination: Path, timeout_seconds: int) -> None:
    command = [
        "svn",
        "export",
        "--force",
        SOURCEFORGE_SVN_TRUNK_URL,
        str(destination),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("SourceForge sync requires `svn` in the API runtime.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"SourceForge sync timed out after {timeout_seconds}s.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"SourceForge sync failed: {detail or 'svn export error'}") from exc


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
    files = [path for path in directory.rglob("*") if path.is_file()]
    total_lines = 0
    total_bytes = 0

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        total_lines += len(content.splitlines())
        total_bytes += len(content.encode("utf-8", errors="ignore"))

    return len(files), total_lines, total_bytes
