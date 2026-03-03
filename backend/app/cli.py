import argparse
import json
from typing import Literal

from app.core.settings import Settings
from app.services.ingestion_service import IngestionService
from app.services.runtime import runtime_services


def main() -> None:
    parser = argparse.ArgumentParser(description="LegacyLens CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Run corpus ingestion")
    ingest_parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Ingestion mode",
    )

    args = parser.parse_args()
    if args.command == "ingest":
        run_ingest(mode=args.mode)


def run_ingest(mode: Literal["full", "incremental"]) -> None:
    settings = Settings()
    with runtime_services(settings) as services:
        ingestion_service = IngestionService(
            settings=services.settings,
            qdrant=services.qdrant,
            openai_gateway=services.openai_gateway,
            tracer=services.tracer,
        )
        stats = ingestion_service.ingest(mode=mode)
    print(json.dumps(stats.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
