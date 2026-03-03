from hashlib import sha1
from pathlib import Path

from app.services.types import SourceFile


def discover_source_files(source_directories: list[str], source_extensions: list[str]) -> list[Path]:
    extensions = {normalize_extension(extension) for extension in source_extensions}
    results: list[Path] = []

    for directory in source_directories:
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            continue

        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                results.append(path)

    results.sort(key=lambda item: str(item))
    return results


def load_source_file(path: Path) -> SourceFile:
    content = read_text_safely(path)
    digest = sha1(content.encode("utf-8", errors="ignore")).hexdigest()

    return SourceFile(path=str(path), text=content, sha1=digest)


def read_text_safely(path: Path) -> str:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_extension(extension: str) -> str:
    normalized = extension.strip().lower()
    if not normalized:
        return normalized
    return normalized if normalized.startswith(".") else f".{normalized}"
