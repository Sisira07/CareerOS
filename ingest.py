from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from boards import ADAPTERS
from db import upsert_job
from gemini_pipeline import process_pending


DEFAULT_CONFIG = Path("boards.json")


def load_configuration(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Board configuration was not found: {path}. "
            "Copy boards.example.json to boards.json."
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("boards.json must contain a JSON list.")

    return data


def resolve_secrets(config: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(config)

    for key, value in list(resolved.items()):
        if isinstance(value, str) and value.startswith("env:"):
            environment_name = value.removeprefix("env:")
            environment_value = os.getenv(environment_name)

            if not environment_value:
                raise RuntimeError(
                    f"Environment variable {environment_name} is missing."
                )

            resolved[key] = environment_value

    return resolved


def ingest_board(config: dict[str, Any]) -> dict[str, Any]:
    adapter_name = str(config["adapter"]).strip().lower()

    if adapter_name not in ADAPTERS:
        raise ValueError(f"Unsupported adapter: {adapter_name}")

    resolved = resolve_secrets(config)
    jobs = ADAPTERS[adapter_name](resolved)

    saved = 0
    rejected = 0

    for job in jobs:
        try:
            upsert_job(job)
            saved += 1
        except Exception as error:
            rejected += 1
            print(
                f"[{adapter_name}] Rejected {job.source_url}: {error}"
            )

    return {
        "adapter": adapter_name,
        "organization": config.get("organization"),
        "fetched": len(jobs),
        "saved": saved,
        "rejected": rejected,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and normalize jobs from configured boards."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--board",
        help="Run only one adapter name, such as greenhouse.",
    )
    parser.add_argument(
        "--process",
        action="store_true",
        help="Run Gemini enrichment after ingestion.",
    )
    parser.add_argument("--process-limit", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    configurations = load_configuration(args.config)

    summaries: list[dict[str, Any]] = []

    for config in configurations:
        if not config.get("enabled", True):
            continue

        if args.board and config.get("adapter") != args.board:
            continue

        try:
            summary = ingest_board(config)
            summaries.append(summary)
            print(
                f"[{summary['adapter']}] "
                f"{summary['organization']}: "
                f"{summary['fetched']} fetched, "
                f"{summary['saved']} saved, "
                f"{summary['rejected']} rejected"
            )
        except Exception as error:
            print(
                f"[{config.get('adapter', 'unknown')}] "
                f"{config.get('organization', 'unknown')}: FAILED — {error}"
            )

    if args.process:
        result = process_pending(args.process_limit)
        print(f"Gemini processing: {result}")

    if not summaries:
        print("No enabled board configurations were processed.")


if __name__ == "__main__":
    main()
