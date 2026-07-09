from pydantic import BaseModel, Field

from src.models.enums import VerificationStatus


class FieldVerificationResult(BaseModel):
    field: str
    initial_result: str = Field(..., description="correct, partial, incorrect, or unchecked.")
    extracted_value: str | None = None
    verified_value: str | None = None
    issue_found: str | None = None
    correction_applied: str | None = None
    changed: bool = False
    final_result: str = Field(..., description="verified, corrected, or needs_review.")


class VerificationCheck(BaseModel):
    app_id: int
    app_name: str
    category: str
    sample_reason: str | list[str]
    fields_checked: list[FieldVerificationResult]
    first_pass_correct_count: int = 0
    first_pass_checked_count: int = 0
    final_status: VerificationStatus
    overall_row_verdict: str = Field(
        default="partial",
        description="pass, partial, corrected, or flagged.",
    )
    notes: str | None = None


class VerificationSummary(BaseModel):
    sample_size: int
    sampling_strategy: str
    sampled_app_ids: list[int] = Field(default_factory=list)
    first_pass_accuracy: float = Field(..., ge=0, le=1)
    first_pass_correct_or_partial_rate: float = Field(default=0, ge=0, le=1)
    post_verification_accuracy: float = Field(..., ge=0, le=1)
    unresolved_after_verification_rate: float = Field(default=0, ge=0, le=1)
    field_accuracy: dict[str, dict[str, int]] = Field(default_factory=dict)
    row_outcomes: dict[str, int] = Field(default_factory=dict)
    confidence_movement: dict[str, dict[str, int]] = Field(default_factory=dict)
    most_common_error_modes: list[str]
    checks: list[VerificationCheck]
