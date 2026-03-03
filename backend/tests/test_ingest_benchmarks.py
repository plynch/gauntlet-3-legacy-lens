from datetime import datetime, timedelta, timezone

from app.models.ingest import IngestStats
from app.services.ingest_benchmarks import append_ingest_run, read_ingest_runs


def make_stats(mode: str, offset_seconds: int) -> IngestStats:
    started = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)
    completed = started + timedelta(seconds=2)
    return IngestStats(
        mode=mode,
        started_at=started,
        completed_at=completed,
        duration_seconds=2.0,
        files_seen=1,
        files_indexed=1,
        files_skipped=0,
        chunks_indexed=2,
        corpus_bytes=100,
        corpus_loc=10,
    )


def test_append_and_read_ingest_runs(tmp_path) -> None:
    log_path = tmp_path / "benchmarks" / "ingest_runs.jsonl"
    append_ingest_run(str(log_path), make_stats("incremental", 0))
    append_ingest_run(str(log_path), make_stats("full", 10))

    runs = read_ingest_runs(str(log_path), limit=5)

    assert len(runs) == 2
    assert runs[0].mode == "full"
    assert runs[1].mode == "incremental"


def test_read_ingest_runs_limits_results(tmp_path) -> None:
    log_path = tmp_path / "benchmarks" / "ingest_runs.jsonl"
    append_ingest_run(str(log_path), make_stats("incremental", 0))
    append_ingest_run(str(log_path), make_stats("full", 10))
    append_ingest_run(str(log_path), make_stats("incremental", 20))

    runs = read_ingest_runs(str(log_path), limit=2)

    assert len(runs) == 2
    assert runs[0].started_at > runs[1].started_at
