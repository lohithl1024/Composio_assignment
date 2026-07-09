import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.models.app_record import AppResearchRecord
from src.models.enums import (
    AccessModel,
    ApiBreadth,
    BuildabilityVerdict,
    ConfidenceLevel,
    McpStatus,
)


DEFAULT_INPUT = Path("data/processed/app_records.verified.jsonl")
DEFAULT_VERIFICATION_SUMMARY = Path("data/processed/verification_summary.json")
DEFAULT_OUTPUT_DIR = Path("data/analysis")


def load_records(path: Path) -> list[AppResearchRecord]:
    with path.open(encoding="utf-8") as file:
        return [AppResearchRecord.model_validate_json(line) for line in file if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_values(values: list[str]) -> dict[str, dict[str, float | int]]:
    total = len(values) or 1
    return {
        key: {"count": count, "pct": round((count / total) * 100, 1)}
        for key, count in Counter(values).most_common()
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def distribution_rows(distribution: dict[str, dict[str, float | int]], label_name: str) -> list[dict[str, Any]]:
    return [
        {label_name: label, "count": stats["count"], "pct": stats["pct"]}
        for label, stats in distribution.items()
    ]


def category_breakdown(records: list[AppResearchRecord]) -> list[dict[str, Any]]:
    by_category: dict[str, list[AppResearchRecord]] = defaultdict(list)
    for record in records:
        by_category[record.category.value].append(record)

    rows = []
    for category, category_records in sorted(by_category.items()):
        total = len(category_records)
        buildable_now = sum(
            1 for record in category_records if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW
        )
        self_serve = sum(
            1
            for record in category_records
            if record.access.model
            in {
                AccessModel.SELF_SERVE_FREE_OR_TRIAL,
                AccessModel.SELF_SERVE_PAID_PLAN_REQUIRED,
            }
        )
        primary_auth = Counter(record.primary_auth_for_toolkit or "unclear" for record in category_records)
        blockers = Counter(record.buildability.primary_blocker.value for record in category_records)
        confidence = Counter(record.confidence.level.value for record in category_records)
        rows.append(
            {
                "category": category,
                "total_apps": total,
                "buildable_now_count": buildable_now,
                "buildable_now_pct": round((buildable_now / total) * 100, 1),
                "self_serve_count": self_serve,
                "self_serve_pct": round((self_serve / total) * 100, 1),
                "most_common_auth": primary_auth.most_common(1)[0][0],
                "most_common_blocker": blockers.most_common(1)[0][0],
                "high_confidence": confidence.get("high", 0),
                "medium_confidence": confidence.get("medium", 0),
                "low_confidence": confidence.get("low", 0),
            }
        )
    return rows


def easy_win_score(record: AppResearchRecord) -> int:
    score = 0
    if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW:
        score += 3
    if record.access.model == AccessModel.SELF_SERVE_FREE_OR_TRIAL:
        score += 2
    if record.access.model == AccessModel.SELF_SERVE_PAID_PLAN_REQUIRED:
        score += 1
    if record.api_surface.breadth in {ApiBreadth.BROAD, ApiBreadth.PLATFORM_LEVEL}:
        score += 2
    elif record.api_surface.breadth == ApiBreadth.MODERATE:
        score += 1
    if record.confidence.level in {ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}:
        score += 2
    if record.buildability.primary_blocker.value == "none":
        score += 1
    if record.mcp.status == McpStatus.OFFICIAL:
        score += 1
    if record.api_surface.webhooks and "yes" in record.api_surface.webhooks.lower():
        score += 1
    return score


def outreach_score(record: AppResearchRecord) -> int:
    score = 0
    if record.buildability.verdict in {
        BuildabilityVerdict.POSSIBLE_BUT_GATED,
        BuildabilityVerdict.BUILDABLE_WITH_CAVEATS,
    }:
        score += 2
    if record.access.model in {
        AccessModel.PARTNER_OR_CONTACT_SALES_GATED,
        AccessModel.ADMIN_OR_WORKSPACE_DEPENDENT,
    }:
        score += 3
    if record.api_surface.breadth in {ApiBreadth.BROAD, ApiBreadth.PLATFORM_LEVEL}:
        score += 2
    if record.buildability.opportunity_score >= 6:
        score += 1
    if record.confidence.level != ConfidenceLevel.LOW:
        score += 1
    return score


def shortlist_rows(records: list[AppResearchRecord], kind: str, limit: int = 20) -> list[dict[str, Any]]:
    if kind == "easy":
        eligible = [
            record
            for record in records
            if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW
            and record.access.model
            in {
                AccessModel.SELF_SERVE_FREE_OR_TRIAL,
                AccessModel.SELF_SERVE_PAID_PLAN_REQUIRED,
            }
            and record.api_surface.has_public_api
            and record.confidence.level != ConfidenceLevel.LOW
        ]
        scored = [(easy_win_score(record), record) for record in eligible]
    else:
        eligible = [
            record
            for record in records
            if record.access.model
            in {
                AccessModel.PARTNER_OR_CONTACT_SALES_GATED,
                AccessModel.ADMIN_OR_WORKSPACE_DEPENDENT,
            }
            or record.buildability.verdict == BuildabilityVerdict.POSSIBLE_BUT_GATED
        ]
        scored = [(outreach_score(record), record) for record in eligible]

    scored.sort(key=lambda item: (-item[0], item[1].app_id))
    return [
        {
            "rank": index + 1,
            "app_name": record.app_name,
            "category": record.category.value,
            "score": score,
            "access_model": record.access.model.value,
            "api_breadth": record.api_surface.breadth.value,
            "buildability_verdict": record.buildability.verdict.value,
            "main_blocker": record.buildability.primary_blocker.value,
            "confidence": record.confidence.level.value,
            "reason": record.buildability.notes,
        }
        for index, (score, record) in enumerate(scored[:limit])
    ]


def dataset_summary(records: list[AppResearchRecord]) -> dict[str, Any]:
    return {
        "total_apps": len(records),
        "with_evidence": sum(1 for record in records if record.evidence),
        "low_confidence_rows": sum(1 for record in records if record.confidence.level == ConfidenceLevel.LOW),
        "sampled_for_verification": sum(1 for record in records if record.verification.sampled_for_human_review),
        "human_review_required": sum(1 for record in records if record.workflow.human_review_required.value == "yes"),
        "with_mcp_evidence": sum(1 for record in records if record.mcp.status == McpStatus.OFFICIAL),
        "with_public_api": sum(1 for record in records if record.api_surface.has_public_api),
    }


def build_headline_findings(
    records: list[AppResearchRecord],
    buildability_distribution: dict[str, dict[str, float | int]],
    access_distribution: dict[str, dict[str, float | int]],
    primary_auth_distribution: dict[str, dict[str, float | int]],
    blocker_counts: dict[str, dict[str, float | int]],
    category_rows: list[dict[str, Any]],
    verification_summary: dict[str, Any],
) -> list[str]:
    buildable_now_pct = buildability_distribution.get("buildable_now", {}).get("pct", 0)
    top_access = next(iter(access_distribution), "unclear")
    top_known_auth = next((auth for auth in primary_auth_distribution if auth != "unclear"), "unclear")
    top_blocker = next((blocker for blocker in blocker_counts if blocker != "none"), "none")
    strongest_category = max(category_rows, key=lambda row: row["buildable_now_pct"]) if category_rows else None
    verification_line = (
        f"The sampled verification audit measured {verification_summary.get('first_pass_accuracy', 0) * 100:.1f}% strict field accuracy and "
        f"{verification_summary.get('first_pass_correct_or_partial_rate', 0) * 100:.1f}% correct-or-partial coverage."
        if verification_summary
        else "Verification summary is pending."
    )

    findings = [
        f"{buildable_now_pct}% of the set is classified as buildable-now in the current verified dataset.",
        f"The most common access model is {top_access}, showing that credential accessibility is a central product-ops filter.",
        f"The most common known primary auth path is {top_known_auth}, while unresolved auth rows stay visible for targeted review.",
        f"The most common non-trivial blocker is {top_blocker}, reinforcing that integration readiness is often limited by access/setup friction rather than API existence alone.",
    ]
    if strongest_category:
        findings.append(
            f"{strongest_category['category']} has the highest buildable-now share in this pass at {strongest_category['buildable_now_pct']}%."
        )
    findings.append(verification_line)
    findings.append(
        "Rows that remain low-confidence or flagged are preserved as review work rather than silently promoted into the final table."
    )
    return findings


def analyze(input_path: Path, verification_summary_path: Path, output_dir: Path) -> dict[str, Any]:
    records = load_records(input_path)
    verification_summary = load_json(verification_summary_path)

    buildability_distribution = count_values([record.buildability.verdict.value for record in records])
    access_distribution = count_values([record.access.model.value for record in records])
    primary_auth_distribution = count_values([record.primary_auth_for_toolkit or "unclear" for record in records])
    all_auth_distribution = count_values([method for record in records for method in record.auth_methods])
    blocker_counts = count_values([record.buildability.primary_blocker.value for record in records])
    confidence_distribution = count_values([record.confidence.level.value for record in records])
    mcp_distribution = count_values([record.mcp.status.value for record in records])
    category_rows = category_breakdown(records)
    easy_wins = shortlist_rows(records, "easy")
    outreach_needed = shortlist_rows(records, "outreach")

    summary = {
        "dataset_summary": dataset_summary(records),
        "buildability_distribution": buildability_distribution,
        "access_model_distribution": access_distribution,
        "primary_auth_distribution": primary_auth_distribution,
        "all_auth_distribution": all_auth_distribution,
        "blocker_counts": blocker_counts,
        "confidence_distribution": confidence_distribution,
        "mcp_distribution": mcp_distribution,
        "category_breakdown": category_rows,
        "easy_wins": easy_wins,
        "outreach_needed": outreach_needed,
        "verification_summary": verification_summary,
        "headline_findings": build_headline_findings(
            records,
            buildability_distribution,
            access_distribution,
            primary_auth_distribution,
            blocker_counts,
            category_rows,
            verification_summary,
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(output_dir / "buildability_distribution.csv", distribution_rows(buildability_distribution, "buildability_verdict"))
    write_csv(output_dir / "access_distribution.csv", distribution_rows(access_distribution, "access_model"))
    write_csv(output_dir / "auth_distribution.csv", distribution_rows(primary_auth_distribution, "primary_auth"))
    write_csv(output_dir / "all_auth_distribution.csv", distribution_rows(all_auth_distribution, "auth_method"))
    write_csv(output_dir / "blocker_counts.csv", distribution_rows(blocker_counts, "main_blocker"))
    write_csv(output_dir / "category_breakdown.csv", category_rows)
    write_csv(output_dir / "easy_wins.csv", easy_wins)
    write_csv(output_dir / "outreach_needed.csv", outreach_needed)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Integration Radar analysis outputs.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--verification-summary", type=Path, default=DEFAULT_VERIFICATION_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = analyze(args.input, args.verification_summary, args.output_dir)
    print(f"Wrote analysis outputs to {args.output_dir}")
    print(f"Total apps: {summary['dataset_summary']['total_apps']}")
    print(f"Easy wins: {len(summary['easy_wins'])}")
    print(f"Outreach-needed: {len(summary['outreach_needed'])}")


if __name__ == "__main__":
    main()
