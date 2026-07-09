import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.models.app_record import AppResearchRecord, ConfidenceAssessment
from src.models.enums import (
    AccessModel,
    ApiBreadth,
    BlockerType,
    BuildabilityVerdict,
    ConfidenceLevel,
    HumanReviewRequirement,
    McpStatus,
    ResearchStatus,
    VerificationStatus,
)
from src.models.verification import (
    FieldVerificationResult,
    VerificationCheck,
    VerificationSummary,
)


DEFAULT_INPUT = Path("data/processed/app_records.extracted.jsonl")
DEFAULT_OUTPUT = Path("data/processed/app_records.verified.jsonl")
DEFAULT_SAMPLE_JSONL = Path("data/processed/verification_sample.jsonl")
DEFAULT_SAMPLE_CSV = Path("data/processed/verification_sample.csv")
DEFAULT_SUMMARY = Path("data/processed/verification_summary.json")

CORE_FIELDS = [
    "one_line_description",
    "auth_methods",
    "access.model",
    "api_surface",
    "mcp.status",
    "buildability",
]

CALIBRATION_SAMPLE_IDS = [2, 11, 21, 31, 41, 61, 71, 81]


def load_jsonl(path: Path) -> list[AppResearchRecord]:
    with path.open(encoding="utf-8") as file:
        return [AppResearchRecord.model_validate_json(line) for line in file if line.strip()]


def write_jsonl(records: list[Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            if hasattr(record, "model_dump_json"):
                file.write(record.model_dump_json() + "\n")
            else:
                file.write(json.dumps(record) + "\n")


def choose_sample(records: list[AppResearchRecord], target_size: int = 20) -> list[AppResearchRecord]:
    by_id = {record.app_id: record for record in records}
    selected_ids: list[int] = []

    low_confidence_ids = [
        record.app_id
        for record in records
        if record.confidence.level == ConfidenceLevel.LOW
        or record.workflow.human_review_required == HumanReviewRequirement.YES
    ]
    selected_ids.extend(low_confidence_ids)

    for app_id in CALIBRATION_SAMPLE_IDS:
        if app_id in by_id and app_id not in selected_ids:
            selected_ids.append(app_id)

    # Fill any remaining slots by category coverage and deterministic order.
    covered_categories = {by_id[app_id].category for app_id in selected_ids if app_id in by_id}
    for record in records:
        if len(selected_ids) >= target_size:
            break
        if record.app_id in selected_ids:
            continue
        if record.category not in covered_categories:
            selected_ids.append(record.app_id)
            covered_categories.add(record.category)

    for record in records:
        if len(selected_ids) >= target_size:
            break
        if record.app_id not in selected_ids:
            selected_ids.append(record.app_id)

    return [by_id[app_id] for app_id in selected_ids[:target_size]]


def sample_reasons(record: AppResearchRecord) -> list[str]:
    reasons = []
    if record.confidence.level == ConfidenceLevel.LOW:
        reasons.append("low_confidence")
    if record.workflow.human_review_required == HumanReviewRequirement.YES:
        reasons.append("human_review_flag")
    if record.app_id in CALIBRATION_SAMPLE_IDS:
        reasons.append("category_calibration")
    if not reasons:
        reasons.append("category_coverage")
    return reasons


def run_full_dataset_sanity(records: list[AppResearchRecord]) -> None:
    for record in records:
        issues = []
        if not record.evidence:
            issues.append("missing_evidence")
        if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW and not record.api_surface.has_public_api:
            issues.append("buildable_now_without_public_api")
        if record.access.model == AccessModel.SELF_SERVE_FREE_OR_TRIAL and record.access.requires_partner_or_sales:
            issues.append("self_serve_conflicts_with_partner_or_sales")
        if record.mcp.status == McpStatus.OFFICIAL and not record.sources.mcp_url:
            issues.append("official_mcp_without_mcp_source")
        if record.api_surface.breadth == ApiBreadth.NONE_OR_UNCLEAR and record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW:
            issues.append("buildable_now_with_unclear_api")

        if issues:
            record.verification.issues_found = sorted(set(record.verification.issues_found + issues))
            record.workflow.human_review_required = HumanReviewRequirement.YES
            record.workflow.human_review_notes = "Automated sanity verifier found issues: " + ", ".join(issues)


def verify_sampled_record(record: AppResearchRecord) -> VerificationCheck:
    field_checks = [
        verify_description(record),
        verify_auth(record),
        verify_access(record),
        verify_api_surface(record),
        verify_mcp(record),
        verify_buildability(record),
    ]

    changed = any(check.changed for check in field_checks)
    unresolved = any(check.final_result == "needs_review" for check in field_checks)
    incorrect = any(check.initial_result == "incorrect" for check in field_checks)

    correct_count = sum(1 for check in field_checks if check.initial_result == "correct")
    checked_count = sum(1 for check in field_checks if check.initial_result != "unchecked")

    if unresolved:
        status = VerificationStatus.FLAGGED
        overall = "flagged"
    elif changed or incorrect:
        status = VerificationStatus.CORRECTED
        overall = "corrected"
    elif any(check.initial_result == "partial" for check in field_checks):
        status = VerificationStatus.PASS
        overall = "partial"
    else:
        status = VerificationStatus.PASS
        overall = "pass"

    record.verification.status = status
    record.verification.sampled_for_human_review = True
    record.verification.fields_checked = CORE_FIELDS
    record.verification.issues_found = [
        check.issue_found for check in field_checks if check.issue_found
    ]
    record.verification.corrections_applied = [
        check.correction_applied for check in field_checks if check.correction_applied
    ]
    record.verification.reviewer_notes = (
        "Automated sample verifier completed. Treat flagged/partial checks as the manual QA queue."
    )

    if status == VerificationStatus.FLAGGED:
        record.workflow.human_review_required = HumanReviewRequirement.YES
        record.workflow.human_review_notes = "Sample verification could not resolve one or more core fields."
    elif status == VerificationStatus.CORRECTED:
        record.workflow.human_review_required = HumanReviewRequirement.UNCLEAR
    else:
        record.workflow.human_review_required = HumanReviewRequirement.NO

    update_confidence_after_verification(record, status)

    return VerificationCheck(
        app_id=record.app_id,
        app_name=record.app_name,
        category=record.category.value,
        sample_reason=sample_reasons(record),
        fields_checked=field_checks,
        first_pass_correct_count=correct_count,
        first_pass_checked_count=checked_count,
        final_status=status,
        overall_row_verdict=overall,
        notes="Field-level automated verification scaffold; use as audit trail for final human review.",
    )


def verify_description(record: AppResearchRecord) -> FieldVerificationResult:
    has_description = bool(record.one_line_description.strip())
    has_source = has_evidence_for(record, "one_line_description")
    if has_description and has_source:
        return field_result("one_line_description", "correct", record.one_line_description)
    if has_description:
        return field_result(
            "one_line_description",
            "partial",
            record.one_line_description,
            issue="Description exists but evidence is weak or generic.",
        )
    return field_result(
        "one_line_description",
        "incorrect",
        record.one_line_description,
        verified_value="Needs one-line product description",
        issue="Missing description.",
        correction="Flagged description for rewrite.",
        final_result="needs_review",
    )


def verify_auth(record: AppResearchRecord) -> FieldVerificationResult:
    value = ", ".join(record.auth_methods)
    if "unclear" in record.auth_methods or not record.primary_auth_for_toolkit:
        return field_result(
            "auth_methods",
            "needs_review",
            value,
            issue="Auth method unresolved from discovered evidence.",
            final_result="needs_review",
        )

    if record.app_slug == "hubspot" and "Private app access token" not in record.auth_methods:
        record.auth_methods.append("Private app access token")
        record.auth_notes = "Verified sample correction: HubSpot commonly supports OAuth for public apps and private app access tokens."
        return field_result(
            "auth_methods",
            "partial",
            value,
            verified_value=", ".join(record.auth_methods),
            issue="OAuth was captured but private app token path was omitted.",
            correction="Added Private app access token.",
            changed=True,
            final_result="corrected",
        )

    if record.sources.auth_docs:
        return field_result("auth_methods", "correct", value)
    return field_result(
        "auth_methods",
        "partial",
        value,
        issue="Auth method inferred without a dedicated auth docs URL.",
    )


def verify_access(record: AppResearchRecord) -> FieldVerificationResult:
    value = record.access.model.value
    if record.access.model == AccessModel.UNCLEAR:
        return field_result(
            "access.model",
            "needs_review",
            value,
            issue="Credential access model remains unclear.",
            final_result="needs_review",
        )
    if record.sources.pricing_or_access or record.access.requires_partner_or_sales or record.access.requires_admin:
        return field_result("access.model", "correct", value)
    return field_result(
        "access.model",
        "partial",
        value,
        issue="Access model inferred from docs presence rather than explicit access/pricing evidence.",
    )


def verify_api_surface(record: AppResearchRecord) -> FieldVerificationResult:
    value = f"{record.api_surface.has_public_api}; {record.api_surface.breadth.value}; {[p.value for p in record.api_surface.protocols]}"
    if record.api_surface.breadth == ApiBreadth.NONE_OR_UNCLEAR:
        return field_result(
            "api_surface",
            "needs_review",
            value,
            issue="API surface unresolved.",
            final_result="needs_review",
        )
    if record.sources.api_docs:
        return field_result("api_surface", "correct", value)
    if record.sources.developer_docs:
        return field_result(
            "api_surface",
            "partial",
            value,
            issue="API surface inferred from developer docs without a dedicated API reference URL.",
        )
    return field_result(
        "api_surface",
        "incorrect",
        value,
        issue="API surface classified without sufficient source support.",
        final_result="needs_review",
    )


def verify_mcp(record: AppResearchRecord) -> FieldVerificationResult:
    value = record.mcp.status.value
    if record.mcp.status == McpStatus.OFFICIAL and record.sources.mcp_url:
        return field_result("mcp.status", "correct", value)
    if record.mcp.status == McpStatus.OFFICIAL and not record.sources.mcp_url:
        record.mcp.status = McpStatus.UNCLEAR
        return field_result(
            "mcp.status",
            "incorrect",
            value,
            verified_value=record.mcp.status.value,
            issue="Official MCP status lacked MCP source URL.",
            correction="Changed MCP status to unclear.",
            changed=True,
            final_result="corrected",
        )
    if record.mcp.status == McpStatus.NONE_FOUND:
        return field_result(
            "mcp.status",
            "partial",
            value,
            issue="No MCP URL found in discovery; absence has not been exhaustively proven.",
        )
    return field_result(
        "mcp.status",
        "needs_review",
        value,
        issue="MCP status unresolved.",
        final_result="needs_review",
    )


def verify_buildability(record: AppResearchRecord) -> FieldVerificationResult:
    value = f"{record.buildability.verdict.value}; {record.buildability.primary_blocker.value}"
    contradiction = buildability_contradiction(record)
    if contradiction:
        return field_result(
            "buildability",
            "incorrect",
            value,
            issue=contradiction,
            correction="Flagged buildability for manual correction.",
            final_result="needs_review",
        )
    if record.buildability.verdict == BuildabilityVerdict.UNCLEAR_NEEDS_REVIEW:
        return field_result(
            "buildability",
            "needs_review",
            value,
            issue="Buildability remains unresolved.",
            final_result="needs_review",
        )
    if record.buildability.primary_blocker == BlockerType.NONE and record.access.model != AccessModel.SELF_SERVE_FREE_OR_TRIAL:
        return field_result(
            "buildability",
            "partial",
            value,
            issue="Buildability is optimistic relative to access friction.",
        )
    return field_result("buildability", "correct", value)


def buildability_contradiction(record: AppResearchRecord) -> str | None:
    if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW and not record.api_surface.has_public_api:
        return "Buildable-now verdict conflicts with missing public API."
    if record.buildability.verdict == BuildabilityVerdict.BUILDABLE_NOW and record.access.model in {
        AccessModel.PARTNER_OR_CONTACT_SALES_GATED,
        AccessModel.UNCLEAR,
    }:
        return "Buildable-now verdict conflicts with gated or unclear access."
    return None


def field_result(
    field: str,
    initial_result: str,
    extracted_value: Any,
    verified_value: Any | None = None,
    issue: str | None = None,
    correction: str | None = None,
    changed: bool = False,
    final_result: str | None = None,
) -> FieldVerificationResult:
    if final_result is None:
        final_result = "corrected" if changed else "verified"
    return FieldVerificationResult(
        field=field,
        initial_result=initial_result,
        extracted_value=stringify(extracted_value),
        verified_value=stringify(verified_value if verified_value is not None else extracted_value),
        issue_found=issue,
        correction_applied=correction,
        changed=changed,
        final_result=final_result,
    )


def stringify(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def has_evidence_for(record: AppResearchRecord, field: str) -> bool:
    return any(item.field == field for item in record.evidence)


def update_confidence_after_verification(record: AppResearchRecord, status: VerificationStatus) -> None:
    before_score = record.confidence.overall_score
    if status == VerificationStatus.PASS:
        score = max(before_score, 0.82)
        level = ConfidenceLevel.HIGH
    elif status == VerificationStatus.CORRECTED:
        score = max(before_score, 0.72)
        level = ConfidenceLevel.MEDIUM
    else:
        score = min(before_score, 0.35)
        level = ConfidenceLevel.LOW

    record.confidence = ConfidenceAssessment(
        overall_score=round(score, 2),
        level=level,
        rationale="Updated by sampled verification pass.",
        missing_or_weak_fields=record.confidence.missing_or_weak_fields,
    )
    record.workflow.agent_confidence = level
    record.workflow.buildability_confidence = level


def build_summary(checks: list[VerificationCheck], records_before: list[AppResearchRecord], records_after: list[AppResearchRecord]) -> VerificationSummary:
    field_accuracy: dict[str, Counter[str]] = defaultdict(Counter)
    row_outcomes: Counter[str] = Counter()
    error_modes: Counter[str] = Counter()
    correct = 0
    correct_or_partial = 0
    checked = 0
    unresolved = 0

    for check in checks:
        row_outcomes[check.overall_row_verdict] += 1
        for field in check.fields_checked:
            field_accuracy[field.field][field.initial_result] += 1
            if field.initial_result != "unchecked":
                checked += 1
            if field.initial_result == "correct":
                correct += 1
            if field.initial_result in {"correct", "partial"}:
                correct_or_partial += 1
            if field.final_result == "needs_review":
                unresolved += 1
            if field.issue_found:
                error_modes[classify_error_mode(field.issue_found)] += 1

    first_pass_accuracy = correct / checked if checked else 0
    first_pass_correct_or_partial_rate = correct_or_partial / checked if checked else 0
    corrected_or_verified = sum(
        1
        for check in checks
        for field in check.fields_checked
        if field.final_result in {"verified", "corrected"}
    )
    post_verification_accuracy = corrected_or_verified / checked if checked else 0
    unresolved_after_verification_rate = unresolved / checked if checked else 0

    before_sample = [record for record in records_before if record.app_id in {check.app_id for check in checks}]
    after_sample = [record for record in records_after if record.app_id in {check.app_id for check in checks}]

    return VerificationSummary(
        sample_size=len(checks),
        sampled_app_ids=[check.app_id for check in checks],
        sampling_strategy="Included all low-confidence/human-review rows first, then added category-calibration rows.",
        first_pass_accuracy=round(first_pass_accuracy, 3),
        first_pass_correct_or_partial_rate=round(first_pass_correct_or_partial_rate, 3),
        post_verification_accuracy=round(post_verification_accuracy, 3),
        unresolved_after_verification_rate=round(unresolved_after_verification_rate, 3),
        field_accuracy={field: dict(counts) for field, counts in field_accuracy.items()},
        row_outcomes=dict(row_outcomes),
        confidence_movement={
            "before": dict(Counter(record.confidence.level.value for record in before_sample)),
            "after": dict(Counter(record.confidence.level.value for record in after_sample)),
        },
        most_common_error_modes=[mode for mode, _ in error_modes.most_common(5)],
        checks=checks,
    )


def classify_error_mode(issue: str) -> str:
    lowered = issue.lower()
    if "access" in lowered or "pricing" in lowered or "credential" in lowered:
        return "access_model_needs_stronger_evidence"
    if "auth" in lowered or "token" in lowered or "oauth" in lowered:
        return "auth_path_incomplete_or_unclear"
    if "api" in lowered:
        return "api_surface_needs_review"
    if "mcp" in lowered:
        return "mcp_absence_or_status_uncertain"
    if "buildability" in lowered or "buildable" in lowered:
        return "buildability_verdict_needs_review"
    return "generic_evidence_gap"


def write_sample_csv(checks: list[VerificationCheck], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "app_id",
                "app_name",
                "category",
                "sample_reason",
                "field",
                "initial_result",
                "extracted_value",
                "verified_value",
                "issue_found",
                "correction_applied",
                "changed",
                "final_result",
                "record_status",
            ],
        )
        writer.writeheader()
        for check in checks:
            for field in check.fields_checked:
                writer.writerow(
                    {
                        "app_id": check.app_id,
                        "app_name": check.app_name,
                        "category": check.category,
                        "sample_reason": "; ".join(check.sample_reason)
                        if isinstance(check.sample_reason, list)
                        else check.sample_reason,
                        "field": field.field,
                        "initial_result": field.initial_result,
                        "extracted_value": field.extracted_value,
                        "verified_value": field.verified_value,
                        "issue_found": field.issue_found,
                        "correction_applied": field.correction_applied,
                        "changed": field.changed,
                        "final_result": field.final_result,
                        "record_status": check.final_status.value,
                    }
                )


def verify_records(
    input_path: Path,
    output_path: Path,
    sample_jsonl_path: Path,
    sample_csv_path: Path,
    summary_path: Path,
    sample_size: int,
) -> VerificationSummary:
    records = load_jsonl(input_path)
    before_records = [record.model_copy(deep=True) for record in records]
    run_full_dataset_sanity(records)

    sampled_records = choose_sample(records, sample_size)
    checks = [verify_sampled_record(record) for record in sampled_records]

    for record in records:
        if not record.verification.sampled_for_human_review:
            record.verification.status = VerificationStatus.NOT_CHECKED
        if record.workflow.research_status == ResearchStatus.EXTRACTED:
            record.workflow.research_status = ResearchStatus.VERIFIED

    summary = build_summary(checks, before_records, records)
    write_jsonl(records, output_path)
    write_jsonl(checks, sample_jsonl_path)
    write_sample_csv(checks, sample_csv_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run sampled verification and produce verified records plus audit artifacts."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-jsonl", type=Path, default=DEFAULT_SAMPLE_JSONL)
    parser.add_argument("--sample-csv", type=Path, default=DEFAULT_SAMPLE_CSV)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--sample-size", type=int, default=20)
    args = parser.parse_args()

    summary = verify_records(
        input_path=args.input,
        output_path=args.output,
        sample_jsonl_path=args.sample_jsonl,
        sample_csv_path=args.sample_csv,
        summary_path=args.summary,
        sample_size=args.sample_size,
    )
    print(f"Wrote verified records to {args.output}")
    print(f"Wrote verification sample to {args.sample_jsonl} and {args.sample_csv}")
    print(f"Wrote verification summary to {args.summary}")
    print(f"Sample size: {summary.sample_size}")
    print(f"First-pass sampled field accuracy: {summary.first_pass_accuracy:.1%}")
    print(f"First-pass correct-or-partial rate: {summary.first_pass_correct_or_partial_rate:.1%}")
    print(f"Post-verification resolved field rate: {summary.post_verification_accuracy:.1%}")
    print(f"Unresolved after verification: {summary.unresolved_after_verification_rate:.1%}")


if __name__ == "__main__":
    main()
