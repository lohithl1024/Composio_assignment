from pydantic import BaseModel, Field, HttpUrl

from src.models.enums import (
    AccessModel,
    ApiBreadth,
    ApiProtocol,
    AppCategory,
    AuthComplexity,
    BlockerType,
    BuildabilityVerdict,
    ConfidenceLevel,
    HumanReviewRequirement,
    McpStatus,
    ResearchStatus,
    SourceType,
    TernaryStatus,
    VerificationStatus,
)


class EvidenceItem(BaseModel):
    field: str = Field(..., description="Schema field supported by this evidence item.")
    claim: str = Field(..., description="The claim this source supports.")
    url: HttpUrl
    source_type: SourceType = SourceType.UNKNOWN
    quote_or_note: str | None = Field(
        default=None,
        description="Short support note or brief quote from the cited page.",
    )
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class DiscoveredSource(BaseModel):
    source_type: str = Field(
        ...,
        description="developer_docs, api_docs, auth_docs, pricing_or_access, mcp, or additional.",
    )
    url: HttpUrl
    title: str | None = None
    is_official: bool = True
    discovery_method: str = Field(
        default="deterministic",
        description="manual_seed, deterministic_hint, guessed_pattern, or search.",
    )


class SourceMap(BaseModel):
    official_site: HttpUrl | None = None
    developer_docs: HttpUrl | None = None
    auth_docs: HttpUrl | None = None
    api_docs: HttpUrl | None = None
    pricing_or_access: HttpUrl | None = None
    mcp_url: HttpUrl | None = None
    mcp_evidence: list[HttpUrl] = Field(default_factory=list)
    additional_source_urls: list[HttpUrl] = Field(default_factory=list)
    discovered_sources: list[DiscoveredSource] = Field(default_factory=list)


class AccessAssessment(BaseModel):
    model: AccessModel
    notes: str
    requires_paid_plan: bool | None = None
    requires_admin: bool | None = None
    requires_app_review_or_approval: bool | None = None
    requires_partner_or_sales: bool | None = None
    free_tier_available: TernaryStatus = TernaryStatus.UNCLEAR
    trial_available: TernaryStatus = TernaryStatus.UNCLEAR
    sandbox_or_test_path: str | None = Field(
        default=None,
        description="yes, limited, no, or unclear with a short explanation.",
    )


class ApiSurface(BaseModel):
    has_public_api: bool | None = None
    protocols: list[ApiProtocol] = Field(default_factory=list)
    breadth: ApiBreadth
    summary: str
    reference_quality: str = Field(
        default="unclear",
        description="excellent, good, mixed, poor, or unclear.",
    )
    supports_read_actions: TernaryStatus = TernaryStatus.UNCLEAR
    supports_write_actions: TernaryStatus = TernaryStatus.UNCLEAR
    webhooks: str | None = Field(
        default=None,
        description="yes, limited, no, or unclear with a short explanation.",
    )


class McpAssessment(BaseModel):
    status: McpStatus
    notes: str
    suitability_notes: str = Field(
        ...,
        description="Whether the app could be wrapped as MCP/agent tools even if no MCP exists.",
    )


class BuildabilityAssessment(BaseModel):
    verdict: BuildabilityVerdict
    primary_blocker: BlockerType = BlockerType.NONE
    secondary_blockers: list[BlockerType] = Field(default_factory=list)
    notes: str
    recommended_toolkit_auth_path: str | None = None
    human_action_needed: str = "unclear"
    opportunity_score: int = Field(
        ...,
        ge=0,
        le=10,
        description="0-10 practical priority score for Composio toolkit expansion.",
    )


class ConfidenceAssessment(BaseModel):
    overall_score: float = Field(..., ge=0, le=1)
    level: ConfidenceLevel
    rationale: str
    missing_or_weak_fields: list[str] = Field(default_factory=list)


class VerificationMetadata(BaseModel):
    status: VerificationStatus = VerificationStatus.NOT_CHECKED
    sampled_for_human_review: bool = False
    fields_checked: list[str] = Field(default_factory=list)
    issues_found: list[str] = Field(default_factory=list)
    corrections_applied: list[str] = Field(default_factory=list)
    reviewer_notes: str | None = None


class WorkflowMetadata(BaseModel):
    research_status: ResearchStatus = ResearchStatus.PENDING
    agent_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    buildability_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    human_review_required: HumanReviewRequirement = HumanReviewRequirement.UNCLEAR
    human_review_notes: str | None = None
    source_count: int = Field(default=0, ge=0)


class AppResearchRecord(BaseModel):
    app_id: int = Field(..., ge=1, le=100)
    app_slug: str
    app_name: str
    category: AppCategory
    website_hint: str
    one_line_description: str

    sources: SourceMap = Field(default_factory=SourceMap)
    auth_methods: list[str] = Field(default_factory=list)
    primary_auth_for_toolkit: str | None = None
    auth_complexity: AuthComplexity = AuthComplexity.UNCLEAR
    auth_notes: str

    access: AccessAssessment
    api_surface: ApiSurface
    mcp: McpAssessment
    buildability: BuildabilityAssessment

    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceAssessment
    verification: VerificationMetadata = Field(default_factory=VerificationMetadata)
    workflow: WorkflowMetadata = Field(default_factory=WorkflowMetadata)

    agent_notes: str | None = Field(
        default=None,
        description="Internal notes from the research/extraction workflow.",
    )
