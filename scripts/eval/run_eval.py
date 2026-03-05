#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LegacyLens retrieval evaluation.")
    parser.add_argument("--api-base", default="http://localhost:8000", help="API base URL")
    parser.add_argument(
        "--queries",
        default="scripts/eval/queries.sample.json",
        help="Path to query JSON file",
    )
    parser.add_argument(
        "--output-markdown",
        default="docs/evaluation-results-local.md",
        help="Where to write markdown report",
    )
    args = parser.parse_args()

    query_specs = load_query_specs(Path(args.queries))
    results = run_queries(args.api_base.rstrip("/"), query_specs)
    report = build_markdown_report(results)
    output_path = Path(args.output_markdown)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote report to {output_path}")


def load_query_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Query file must be a JSON array.")
    return payload


def run_queries(api_base: str, query_specs: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    precision_scores: list[float] = []
    citation_hits = 0

    for spec in query_specs:
        question = str(spec["question"])
        expected_paths = [str(path) for path in spec.get("expected_paths", [])]
        expected_path_contains = [str(item) for item in spec.get("expected_path_contains", [])]
        expected_set = set(expected_paths)

        started = time.perf_counter()
        payload = post_json(
            f"{api_base}/api/query",
            {"question": question},
            timeout_seconds=30,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(elapsed_ms)

        snippets = payload.get("snippets", [])[:5]
        snippet_paths = [str(item.get("citation", {}).get("path", "")) for item in snippets]
        relevant_count = count_relevant(snippet_paths, expected_set, expected_path_contains)
        precision_at_5 = relevant_count / 5.0
        precision_scores.append(precision_at_5)

        citation_paths = [str(item.get("path", "")) for item in payload.get("citations", [])]
        citation_match = has_expected_path(citation_paths, expected_set, expected_path_contains)
        if citation_match:
            citation_hits += 1

        rows.append(
            {
                "question": question,
                "latency_ms": elapsed_ms,
                "precision_at_5": precision_at_5,
                "citation_match": citation_match,
            }
        )

    count = len(rows) or 1
    return {
        "rows": rows,
        "summary": {
            "queries": len(rows),
            "latency_p50_ms": percentile(latencies_ms, 50),
            "latency_p95_ms": percentile(latencies_ms, 95),
            "mean_precision_at_5": sum(precision_scores) / count,
            "citation_match_rate": citation_hits / count,
        },
    }


def count_relevant(paths: list[str], expected_paths: set[str], expected_path_contains: list[str]) -> int:
    return sum(1 for path in paths if path_matches(path, expected_paths, expected_path_contains))


def has_expected_path(paths: list[str], expected_paths: set[str], expected_path_contains: list[str]) -> bool:
    return any(path_matches(path, expected_paths, expected_path_contains) for path in paths)


def path_matches(path: str, expected_paths: set[str], expected_path_contains: list[str]) -> bool:
    if path in expected_paths:
        return True

    return any(fragment in path for fragment in expected_path_contains)


def percentile(values: list[float], value: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (value / 100) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def post_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def build_markdown_report(results: dict[str, Any]) -> str:
    summary = results["summary"]
    rows = results["rows"]
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Evaluation Results",
        "",
        f"Generated at: {generated_at}",
        "",
        "## Summary",
        "",
        f"- Queries: {summary['queries']}",
        f"- Latency p50: {summary['latency_p50_ms']:.1f} ms",
        f"- Latency p95: {summary['latency_p95_ms']:.1f} ms",
        f"- Mean Precision@5: {summary['mean_precision_at_5']:.3f}",
        f"- Citation match rate: {summary['citation_match_rate']:.3f}",
        "",
        "## Per Query",
        "",
        "| Question | Latency (ms) | Precision@5 | Citation Match |",
        "| --- | ---: | ---: | --- |",
    ]

    for row in rows:
        lines.append(
            f"| {row['question']} | {row['latency_ms']:.1f} | {row['precision_at_5']:.3f} | "
            f"{'yes' if row['citation_match'] else 'no'} |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    main()
