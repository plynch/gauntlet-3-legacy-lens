import json
from pathlib import Path

from app.models.ingest import IngestStats


def append_ingest_run(log_path: str, stats: IngestStats) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(stats.model_dump(mode="json"), ensure_ascii=True) + "\n")


def read_ingest_runs(log_path: str, limit: int = 20) -> list[IngestStats]:
    path = Path(log_path)
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    recent = lines[-max(limit, 0) :]
    results: list[IngestStats] = []

    for line in reversed(recent):
        if not line.strip():
            continue
        results.append(IngestStats.model_validate_json(line))

    return results
