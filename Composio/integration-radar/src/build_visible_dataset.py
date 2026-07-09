import argparse
import csv
import json
from pathlib import Path
from typing import Any

from src.models.app_record import AppResearchRecord


DEFAULT_INPUT = Path("data/processed/app_records.verified.jsonl")
DEFAULT_OUTPUT_CSV = Path("data/final/app_research_final.csv")
DEFAULT_OUTPUT_JSON = Path("data/final/app_research_final.json")


def load_records(path: Path) -> list[AppResearchRecord]:
    with path.open(encoding="utf-8") as file:
        return [AppResearchRecord.model_validate_json(line) for line in file if line.strip()]


def flatten_record(record: AppResearchRecord) -> dict[str, Any]:
    evidence_urls = sorted({str(item.url) for item in record.evidence})
    return {
        "app_id": record.app_id,
        "app_name": record.app_name,
        "category": record.category.value,
        "what_it_does": record.one_line_description,
        "auth_methods": ", ".join(record.auth_methods),
        "primary_auth_for_toolkit": record.primary_auth_for_toolkit or "unclear",
        "auth_complexity": record.auth_complexity.value,
        "access_model": record.access.model.value,
        "access_notes": record.access.notes,
        "public_api": "yes" if record.api_surface.has_public_api else "no_or_unclear",
        "api_protocols": ", ".join(protocol.value for protocol in record.api_surface.protocols),
        "api_breadth": record.api_surface.breadth.value,
        "api_surface_summary": record.api_surface.summary,
        "mcp_status": record.mcp.status.value,
        "mcp_url": str(record.sources.mcp_url) if record.sources.mcp_url else "",
        "buildability_verdict": record.buildability.verdict.value,
        "main_blocker": record.buildability.primary_blocker.value,
        "opportunity_score": record.buildability.opportunity_score,
        "confidence": record.confidence.level.value,
        "confidence_score": record.confidence.overall_score,
        "verification_status": record.verification.status.value,
        "human_review_required": record.workflow.human_review_required.value,
        "developer_docs_url": str(record.sources.developer_docs) if record.sources.developer_docs else "",
        "api_docs_url": str(record.sources.api_docs) if record.sources.api_docs else "",
        "auth_docs_url": str(record.sources.auth_docs) if record.sources.auth_docs else "",
        "pricing_or_access_url": str(record.sources.pricing_or_access) if record.sources.pricing_or_access else "",
        "evidence_urls": " | ".join(evidence_urls),
        "notes_short": notes_short(record),
    }


def notes_short(record: AppResearchRecord) -> str:
    blocker = record.buildability.primary_blocker.value
    if record.buildability.verdict.value == "buildable_now":
        return f"{record.api_surface.breadth.value} API surface with {record.access.model.value} access; first-pass toolkit candidate."
    if blocker != "none":
        return f"{record.buildability.verdict.value}; primary blocker is {blocker}."
    return record.buildability.notes


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def build_visible_dataset(input_path: Path, output_csv: Path, output_json: Path) -> list[dict[str, Any]]:
    records = load_records(input_path)
    rows = [flatten_record(record) for record in records]
    write_csv(output_csv, rows)
    write_json(output_json, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Flatten verified records into reviewer-facing CSV/JSON.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    args = parser.parse_args()

    rows = build_visible_dataset(args.input, args.output_csv, args.output_json)
    print(f"Wrote {len(rows)} rows to {args.output_csv}")
    print(f"Wrote {len(rows)} rows to {args.output_json}")


if __name__ == "__main__":
    main()
