import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from src.models.app_record import (
    AccessAssessment,
    ApiSurface,
    AppResearchRecord,
    BuildabilityAssessment,
    ConfidenceAssessment,
    McpAssessment,
)
from src.models.enums import (
    AccessModel,
    ApiBreadth,
    AppCategory,
    BlockerType,
    BuildabilityVerdict,
    ConfidenceLevel,
    McpStatus,
)


DEFAULT_INPUT = Path("data/input/apps.csv")
DEFAULT_OUTPUT = Path("data/processed/app_records.stub.jsonl")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def load_apps_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [normalize_app_row(row) for row in reader]


def normalize_app_row(row: dict[str, Any]) -> dict[str, str]:
    normalized = {normalize_key(key): (value or "").strip() for key, value in row.items()}

    app_id = normalized.get("app_id") or normalized.get("id") or normalized.get("#")
    app_name = (
        normalized.get("app_name")
        or normalized.get("app")
        or normalized.get("name")
        or normalized.get("product")
    )
    category = normalized.get("category")
    website_hint = (
        normalized.get("website_hint")
        or normalized.get("website")
        or normalized.get("hint")
        or normalized.get("website_or_hint")
    )

    missing = [
        field
        for field, value in {
            "app_id": app_id,
            "app_name": app_name,
            "category": category,
            "website_hint": website_hint,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required fields {missing} in row: {row}")

    return {
        "app_id": app_id,
        "app_name": app_name,
        "category": category,
        "website_hint": website_hint,
    }


def make_stub_record(row: dict[str, str]) -> AppResearchRecord:
    return AppResearchRecord(
        app_id=int(row["app_id"]),
        app_slug=slugify(row["app_name"]),
        app_name=row["app_name"],
        category=AppCategory(row["category"]),
        website_hint=row["website_hint"],
        one_line_description="",
        auth_methods=[],
        auth_notes="Pending research.",
        access=AccessAssessment(
            model=AccessModel.UNCLEAR,
            notes="Pending source discovery and access classification.",
        ),
        api_surface=ApiSurface(
            has_public_api=None,
            protocols=[],
            breadth=ApiBreadth.NONE_OR_UNCLEAR,
            summary="Pending API surface research.",
        ),
        mcp=McpAssessment(
            status=McpStatus.UNCLEAR,
            notes="Pending MCP discovery.",
            suitability_notes="Pending toolkit suitability assessment.",
        ),
        buildability=BuildabilityAssessment(
            verdict=BuildabilityVerdict.UNCLEAR_NEEDS_REVIEW,
            primary_blocker=BlockerType.UNKNOWN,
            notes="Pending buildability assessment.",
            opportunity_score=0,
        ),
        confidence=ConfidenceAssessment(
            overall_score=0.0,
            level=ConfidenceLevel.LOW,
            rationale="Stub record created from assignment app list only.",
            missing_or_weak_fields=[
                "one_line_description",
                "sources",
                "auth_methods",
                "access",
                "api_surface",
                "mcp",
                "buildability",
                "evidence",
            ],
        ),
        agent_notes="Initialized by bootstrap_records.py; no web research has run yet.",
    )


def write_jsonl(records: list[AppResearchRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json() + "\n")


def bootstrap_records(input_path: Path, output_path: Path) -> list[AppResearchRecord]:
    rows = load_apps_csv(input_path)
    records = [make_stub_record(row) for row in rows]
    write_jsonl(records, output_path)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create validated stub AppResearchRecord JSONL rows from apps.csv."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = bootstrap_records(args.input, args.output)
    print(f"Wrote {len(records)} stub records to {args.output}")


if __name__ == "__main__":
    main()
