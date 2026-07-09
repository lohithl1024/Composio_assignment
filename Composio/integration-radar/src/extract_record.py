import argparse
from pathlib import Path

from pydantic import HttpUrl

from src.models.app_record import (
    AccessAssessment,
    ApiSurface,
    AppResearchRecord,
    BuildabilityAssessment,
    ConfidenceAssessment,
    EvidenceItem,
    McpAssessment,
)
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
)
from src.source_packet import ResearchPacket, build_source_packet


DEFAULT_INPUT = Path("data/processed/app_records.discovered.jsonl")
DEFAULT_OUTPUT = Path("data/processed/app_records.extracted.jsonl")


API_KEY_FIRST = {
    "twilio",
    "close",
    "copper",
    "dataforseo",
    "se_ranking",
    "ahrefs",
    "mrscraper",
    "apify",
    "firecrawl",
    "bright_data",
    "stripe",
    "binance",
    "vercel",
    "cloudflare",
    "datadog",
    "sentry",
    "gumroad",
    "ecwid",
    "sendgrid",
    "youtube_transcript",
}

OAUTH_FIRST = {
    "salesforce",
    "hubspot",
    "pipedrive",
    "podio",
    "zoho_crm",
    "zendesk",
    "intercom",
    "front",
    "help_scout",
    "slack",
    "discord",
    "google_ads",
    "meta_ads",
    "linkedin_ads",
    "mailchimp",
    "pinterest",
    "shopify",
    "github",
    "notion",
    "airtable",
    "linear",
    "jira",
    "asana",
    "monday_com",
    "harvest",
    "quickbooks",
    "xero",
}

GATED_APPS = {
    "google_ads",
    "meta_ads",
    "linkedin_ads",
    "amazon_selling_partner",
    "pitchbook",
    "paygent_connect",
    "notebooklm",
    "salesforce_commerce_cloud",
}

ADMIN_DEPENDENT_APPS = {
    "salesforce",
    "hubspot",
    "zendesk",
    "slack",
    "zoho_crm",
    "jira",
    "monday_com",
    "smartsheet",
    "snowflake",
    "mongodb_atlas",
    "quickbooks",
    "xero",
    "shopify",
    "bigcommerce",
}

PAID_PLAN_APPS = {
    "ahrefs",
    "bright_data",
    "dataforseo",
    "clay",
    "waterfall_io",
    "brex",
    "ramp",
    "dealcloud",
}

NARROW_OR_NON_API_APPS = {
    "sherlock",
    "mermaid_cli",
    "fanbasis",
    "consensus",
    "higgsfield",
    "fathom",
    "grain",
}

GRAPHQL_APPS = {"linear", "monday_com", "shopify", "github", "snowflake"}

SOAP_OR_ENTERPRISE_APPS = {"salesforce", "magento_adobe_commerce"}

PLATFORM_LEVEL_APPS = {
    "salesforce",
    "hubspot",
    "shopify",
    "github",
    "cloudflare",
    "jira",
    "zoho_crm",
    "magento_adobe_commerce",
}

BROAD_APPS = {
    "zendesk",
    "intercom",
    "slack",
    "twilio",
    "google_ads",
    "meta_ads",
    "mailchimp",
    "klaviyo",
    "bigcommerce",
    "amazon_selling_partner",
    "apify",
    "vercel",
    "netlify",
    "datadog",
    "notion",
    "airtable",
    "asana",
    "stripe",
    "plaid",
    "quickbooks",
    "xero",
}


DESCRIPTION_BY_CATEGORY = {
    AppCategory.CRM_AND_SALES: "CRM and sales platform for managing customer records, deals, and revenue workflows",
    AppCategory.SUPPORT_AND_HELPDESK: "customer support platform for managing conversations, tickets, and service workflows",
    AppCategory.COMMUNICATIONS_AND_MESSAGING: "communications platform for messaging, calls, notifications, or collaboration workflows",
    AppCategory.MARKETING_ADS_EMAIL_SOCIAL: "marketing, ads, email, or social platform for campaign and audience workflows",
    AppCategory.ECOMMERCE: "ecommerce platform for stores, products, orders, customers, and commerce operations",
    AppCategory.DATA_SEO_SCRAPING: "data, SEO, scraping, or enrichment platform for collecting and operationalizing web or business data",
    AppCategory.DEVELOPER_INFRA_DATA: "developer, infrastructure, or data platform for engineering and operational workflows",
    AppCategory.PRODUCTIVITY_PROJECT_MANAGEMENT: "productivity or project management platform for tasks, docs, teams, and workflow coordination",
    AppCategory.FINANCE_FINTECH: "finance or fintech platform for payments, accounting, banking, spend, or financial data workflows",
    AppCategory.AI_RESEARCH_MEDIA: "AI, research, meeting, or media-native product for knowledge, content, or automation workflows",
}


def load_jsonl(path: Path) -> list[AppResearchRecord]:
    with path.open(encoding="utf-8") as file:
        return [AppResearchRecord.model_validate_json(line) for line in file if line.strip()]


def write_jsonl(records: list[AppResearchRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json() + "\n")


def extract_record(record: AppResearchRecord, fetch: bool = False) -> AppResearchRecord:
    packet = build_source_packet(record, fetch=fetch)
    source_count = len(packet.sources)

    record.one_line_description = description_for(record)
    record.auth_methods = infer_auth_methods(record, packet)
    record.primary_auth_for_toolkit = choose_primary_auth(record.auth_methods)
    record.auth_complexity = infer_auth_complexity(record)
    record.auth_notes = auth_notes_for(record)

    record.access = infer_access(record)
    record.api_surface = infer_api_surface(record)
    record.mcp = infer_mcp(record)
    record.buildability = infer_buildability(record)
    record.evidence = build_evidence(record)
    record.confidence = infer_confidence(record, packet)

    record.workflow.research_status = ResearchStatus.EXTRACTED
    record.workflow.agent_confidence = record.confidence.level
    record.workflow.buildability_confidence = record.confidence.level
    record.workflow.human_review_required = (
        HumanReviewRequirement.YES
        if record.confidence.level == ConfidenceLevel.LOW
        or record.buildability.verdict == BuildabilityVerdict.UNCLEAR_NEEDS_REVIEW
        else HumanReviewRequirement.UNCLEAR
    )
    if record.workflow.human_review_required == HumanReviewRequirement.YES:
        record.workflow.human_review_notes = "Low-confidence first-pass extraction; targeted verification needed."
    record.agent_notes = append_agent_note(
        record.agent_notes,
        "extract_record.py filled first-pass fields from discovered source packet and deterministic rubric heuristics.",
    )
    return record


def description_for(record: AppResearchRecord) -> str:
    return f"{record.app_name} is a {DESCRIPTION_BY_CATEGORY[record.category]}."


def infer_auth_methods(record: AppResearchRecord, packet: ResearchPacket) -> list[str]:
    slug = record.app_slug
    text = " ".join(f"{source.url} {source.title or ''} {source.snippet}" for source in packet.sources).lower()
    methods: list[str] = []

    if slug in OAUTH_FIRST or "oauth" in text:
        methods.append("OAuth 2.0")
    if slug in API_KEY_FIRST or "api key" in text or "token" in text:
        methods.append("API key / bearer token")
    if slug in {"github"}:
        methods.extend(["GitHub App auth", "personal access token"])
    if slug in {"salesforce"}:
        methods.append("JWT bearer flow")
    if slug in {"telegram"}:
        methods.append("Bot token")
    if slug in {"mermaid_cli", "sherlock"}:
        methods.append("No hosted app auth / CLI or open-source usage")
    if record.sources.auth_docs and not methods:
        methods.append("Documented auth flow")
    if not methods:
        methods.append("unclear")

    return dedupe(methods)


def choose_primary_auth(methods: list[str]) -> str | None:
    for preferred in ("OAuth 2.0", "API key / bearer token", "GitHub App auth", "Bot token"):
        if preferred in methods:
            return preferred
    return methods[0] if methods and methods[0] != "unclear" else None


def infer_auth_complexity(record: AppResearchRecord) -> AuthComplexity:
    if record.app_slug in GATED_APPS or record.app_slug in SOAP_OR_ENTERPRISE_APPS:
        return AuthComplexity.COMPLEX
    if "OAuth 2.0" in record.auth_methods or record.app_slug in ADMIN_DEPENDENT_APPS:
        return AuthComplexity.MODERATE
    if record.primary_auth_for_toolkit:
        return AuthComplexity.SIMPLE
    return AuthComplexity.UNCLEAR


def auth_notes_for(record: AppResearchRecord) -> str:
    if record.primary_auth_for_toolkit:
        return f"First-pass extraction suggests {record.primary_auth_for_toolkit} as the likely toolkit auth path."
    return "Auth path unclear from discovered sources; requires targeted lookup."


def infer_access(record: AppResearchRecord) -> AccessAssessment:
    slug = record.app_slug
    if slug in GATED_APPS:
        return AccessAssessment(
            model=AccessModel.PARTNER_OR_CONTACT_SALES_GATED,
            notes="First-pass rubric marks this app as gated because access commonly depends on app review, partner approval, business verification, or sales contact.",
            requires_paid_plan=None,
            requires_admin=True,
            requires_app_review_or_approval=True,
            requires_partner_or_sales=True,
            free_tier_available=TernaryStatus.UNCLEAR,
            trial_available=TernaryStatus.UNCLEAR,
            sandbox_or_test_path="unclear; needs verification",
        )
    if slug in ADMIN_DEPENDENT_APPS:
        return AccessAssessment(
            model=AccessModel.ADMIN_OR_WORKSPACE_DEPENDENT,
            notes="Credentials appear tied to an org, workspace, tenant, or app installation context.",
            requires_paid_plan=slug in PAID_PLAN_APPS,
            requires_admin=True,
            requires_app_review_or_approval=False,
            requires_partner_or_sales=False,
            free_tier_available=TernaryStatus.UNCLEAR,
            trial_available=TernaryStatus.UNCLEAR,
            sandbox_or_test_path="unclear; needs verification",
        )
    if slug in PAID_PLAN_APPS:
        return AccessAssessment(
            model=AccessModel.SELF_SERVE_PAID_PLAN_REQUIRED,
            notes="Likely self-serve API access, but useful access may depend on a paid plan or commercial account.",
            requires_paid_plan=True,
            requires_admin=False,
            requires_app_review_or_approval=False,
            requires_partner_or_sales=False,
            free_tier_available=TernaryStatus.UNCLEAR,
            trial_available=TernaryStatus.UNCLEAR,
            sandbox_or_test_path="unclear; needs verification",
        )
    if record.workflow.source_count <= 1:
        return AccessAssessment(
            model=AccessModel.UNCLEAR,
            notes="Insufficient discovered sources to classify credential access.",
            sandbox_or_test_path="unclear",
        )
    return AccessAssessment(
        model=AccessModel.SELF_SERVE_FREE_OR_TRIAL,
        notes="First-pass extraction found public developer/API documentation and no obvious discovery-stage sales or partner gate.",
        requires_paid_plan=False,
        requires_admin=False,
        requires_app_review_or_approval=False,
        requires_partner_or_sales=False,
        free_tier_available=TernaryStatus.UNCLEAR,
        trial_available=TernaryStatus.UNCLEAR,
        sandbox_or_test_path="unclear; needs verification",
    )


def infer_api_surface(record: AppResearchRecord) -> ApiSurface:
    protocols = infer_protocols(record)
    has_public_api = bool(record.sources.api_docs or record.sources.developer_docs) and record.app_slug not in NARROW_OR_NON_API_APPS

    if record.app_slug in PLATFORM_LEVEL_APPS:
        breadth = ApiBreadth.PLATFORM_LEVEL
    elif record.app_slug in BROAD_APPS:
        breadth = ApiBreadth.BROAD
    elif record.app_slug in NARROW_OR_NON_API_APPS:
        breadth = ApiBreadth.NARROW if has_public_api else ApiBreadth.NONE_OR_UNCLEAR
    elif has_public_api:
        breadth = ApiBreadth.MODERATE
    else:
        breadth = ApiBreadth.NONE_OR_UNCLEAR

    return ApiSurface(
        has_public_api=has_public_api,
        protocols=protocols,
        breadth=breadth,
        summary=api_summary_for(record, breadth, protocols),
        reference_quality="good" if record.sources.api_docs else "unclear",
        supports_read_actions=TernaryStatus.YES if has_public_api else TernaryStatus.UNCLEAR,
        supports_write_actions=TernaryStatus.YES if breadth in {ApiBreadth.BROAD, ApiBreadth.PLATFORM_LEVEL} else TernaryStatus.UNCLEAR,
        webhooks="yes or likely" if ApiProtocol.WEBHOOKS in protocols else "unclear; needs verification",
    )


def infer_protocols(record: AppResearchRecord) -> list[ApiProtocol]:
    protocols: list[ApiProtocol] = []
    if record.sources.api_docs or record.sources.developer_docs:
        protocols.append(ApiProtocol.REST)
    if record.app_slug in GRAPHQL_APPS:
        protocols.append(ApiProtocol.GRAPHQL)
    if record.app_slug in SOAP_OR_ENTERPRISE_APPS:
        protocols.append(ApiProtocol.SOAP)
    if record.category in {
        AppCategory.CRM_AND_SALES,
        AppCategory.SUPPORT_AND_HELPDESK,
        AppCategory.ECOMMERCE,
        AppCategory.PRODUCTIVITY_PROJECT_MANAGEMENT,
        AppCategory.DEVELOPER_INFRA_DATA,
    }:
        protocols.append(ApiProtocol.WEBHOOKS)
    if record.sources.mcp_url:
        protocols.append(ApiProtocol.MCP)
    if not protocols:
        protocols.append(ApiProtocol.UNKNOWN)
    return list(dict.fromkeys(protocols))


def api_summary_for(record: AppResearchRecord, breadth: ApiBreadth, protocols: list[ApiProtocol]) -> str:
    protocol_text = ", ".join(protocol.value for protocol in protocols)
    return f"First-pass API surface classified as {breadth.value} using discovered {protocol_text} source evidence."


def infer_mcp(record: AppResearchRecord) -> McpAssessment:
    if record.sources.mcp_url:
        return McpAssessment(
            status=McpStatus.OFFICIAL,
            notes="MCP source URL was discovered during source discovery.",
            suitability_notes="Official MCP evidence makes this a direct agent-callable candidate, subject to access verification.",
        )
    if record.sources.api_docs or record.sources.developer_docs:
        return McpAssessment(
            status=McpStatus.NONE_FOUND,
            notes="No MCP URL found in discovery.",
            suitability_notes="Public API/docs suggest this may still be wrapped as Composio tools or an MCP server.",
        )
    return McpAssessment(
        status=McpStatus.UNCLEAR,
        notes="No strong developer/API source found yet.",
        suitability_notes="Toolkit suitability needs targeted source discovery.",
    )


def infer_buildability(record: AppResearchRecord) -> BuildabilityAssessment:
    if record.access.model == AccessModel.PARTNER_OR_CONTACT_SALES_GATED:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.POSSIBLE_BUT_GATED,
            primary_blocker=BlockerType.APP_REVIEW_OR_BUSINESS_VERIFICATION,
            secondary_blockers=[BlockerType.PARTNER_GATED_ACCESS],
            notes="API may be useful, but practical toolkit access likely depends on approval, verification, sales, or partnership.",
            recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
            human_action_needed="verify access gate and credential path",
            opportunity_score=5,
        )
    if not record.api_surface.has_public_api:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.UNCLEAR_NEEDS_REVIEW,
            primary_blocker=BlockerType.UNCLEAR_ACCESS,
            notes="Insufficient public API/source evidence for a confident buildability verdict.",
            recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
            human_action_needed="targeted docs lookup",
            opportunity_score=2,
        )
    if record.api_surface.breadth == ApiBreadth.NONE_OR_UNCLEAR:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.NOT_PRACTICAL_TODAY,
            primary_blocker=BlockerType.NO_PUBLIC_API,
            notes="No sufficiently clear public API surface found in discovered sources.",
            human_action_needed="manual review",
            opportunity_score=1,
        )
    if record.api_surface.breadth == ApiBreadth.NARROW:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.BUILDABLE_WITH_CAVEATS,
            primary_blocker=BlockerType.API_TOO_NARROW,
            notes="Likely buildable for a narrow action set, but toolkit value may be limited.",
            recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
            human_action_needed="verify practical action coverage",
            opportunity_score=5,
        )
    if record.access.model == AccessModel.ADMIN_OR_WORKSPACE_DEPENDENT:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.BUILDABLE_WITH_CAVEATS,
            primary_blocker=BlockerType.ADMIN_SETUP_REQUIRED,
            notes="Technically buildable, but installation and credential setup likely depend on an admin or workspace owner.",
            recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
            human_action_needed="verify admin setup path",
            opportunity_score=7,
        )
    if record.access.model == AccessModel.SELF_SERVE_PAID_PLAN_REQUIRED:
        return BuildabilityAssessment(
            verdict=BuildabilityVerdict.BUILDABLE_WITH_CAVEATS,
            primary_blocker=BlockerType.PAID_PLAN_REQUIRED,
            notes="Technically buildable, but useful API access may require paid access.",
            recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
            human_action_needed="verify pricing/API access terms",
            opportunity_score=6,
        )
    return BuildabilityAssessment(
        verdict=BuildabilityVerdict.BUILDABLE_NOW,
        primary_blocker=BlockerType.NONE,
        notes="Public docs, workable auth, and moderate-or-better API surface make this a first-pass build-now candidate.",
        recommended_toolkit_auth_path=record.primary_auth_for_toolkit,
        human_action_needed="normal implementation QA",
        opportunity_score=8 if record.api_surface.breadth == ApiBreadth.MODERATE else 9,
    )


def build_evidence(record: AppResearchRecord) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    add_evidence(evidence, record, "one_line_description", record.one_line_description, preferred=("official_site", "developer_docs"))
    add_evidence(evidence, record, "auth_methods", ", ".join(record.auth_methods), preferred=("auth_docs", "developer_docs"))
    add_evidence(evidence, record, "access.model", record.access.model.value, preferred=("pricing_or_access", "auth_docs", "developer_docs"))
    add_evidence(evidence, record, "api_surface.breadth", record.api_surface.breadth.value, preferred=("api_docs", "developer_docs"))
    add_evidence(evidence, record, "mcp.status", record.mcp.status.value, preferred=("mcp_url", "developer_docs"))
    add_evidence(evidence, record, "buildability.verdict", record.buildability.verdict.value, preferred=("api_docs", "auth_docs", "pricing_or_access", "developer_docs"))
    return evidence


def add_evidence(
    evidence: list[EvidenceItem],
    record: AppResearchRecord,
    field: str,
    claim: str,
    preferred: tuple[str, ...],
) -> None:
    source_url = first_source_url(record, preferred)
    if not source_url:
        return
    evidence.append(
        EvidenceItem(
            field=field,
            claim=claim,
            url=source_url,
            source_type=source_type_for(field),
            quote_or_note="First-pass evidence link from discovered source packet; verify exact claim support in Module 4.",
            confidence=ConfidenceLevel.MEDIUM,
        )
    )


def first_source_url(record: AppResearchRecord, preferred: tuple[str, ...]) -> HttpUrl | None:
    for field in preferred:
        value = getattr(record.sources, field, None)
        if value:
            return value
    if record.sources.discovered_sources:
        return record.sources.discovered_sources[0].url
    return None


def source_type_for(field: str) -> SourceType:
    if "access" in field:
        return SourceType.PRICING_OR_ACCESS_PAGE
    if "description" in field:
        return SourceType.DEVELOPER_PORTAL
    return SourceType.OFFICIAL_DOCS


def infer_confidence(record: AppResearchRecord, packet: ResearchPacket) -> ConfidenceAssessment:
    missing = []
    source_count = len(packet.sources)
    fetched_source_count = sum(1 for source in packet.sources if source.fetched)
    score = 0.25
    if record.sources.developer_docs:
        score += 0.15
    else:
        missing.append("developer_docs")
    if record.sources.api_docs:
        score += 0.15
    else:
        missing.append("api_docs")
    if record.sources.auth_docs:
        score += 0.15
    else:
        missing.append("auth_docs")
    if record.sources.pricing_or_access:
        score += 0.1
    else:
        missing.append("pricing_or_access")
    if len(record.evidence) >= 4:
        score += 0.15
    if record.access.model != AccessModel.UNCLEAR and record.buildability.verdict != BuildabilityVerdict.UNCLEAR_NEEDS_REVIEW:
        score += 0.1
    if source_count <= 1:
        score -= 0.2
    if fetched_source_count == 0:
        score = min(score, 0.68)
        missing.append("fetched_source_text")

    score = max(0.0, min(1.0, score))
    if score >= 0.75:
        level = ConfidenceLevel.HIGH
    elif score >= 0.45:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return ConfidenceAssessment(
        overall_score=round(score, 2),
        level=level,
        rationale="Confidence reflects discovered source coverage, evidence count, and whether core fields remain unclear.",
        missing_or_weak_fields=missing,
    )


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def append_agent_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    return f"{existing}\n{note}"


def extract_records(input_path: Path, output_path: Path, fetch: bool = False) -> list[AppResearchRecord]:
    records = load_jsonl(input_path)
    extracted = [extract_record(record, fetch=fetch) for record in records]
    write_jsonl(extracted, output_path)
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill first-pass research fields from discovered source packets."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch source pages before extraction. Default uses discovered URL/title packets only.",
    )
    args = parser.parse_args()

    records = extract_records(args.input, args.output, fetch=args.fetch)
    low_confidence = sum(1 for record in records if record.confidence.level == ConfidenceLevel.LOW)
    with_evidence = sum(1 for record in records if record.evidence)
    print(f"Wrote {len(records)} extracted records to {args.output}")
    print(f"Records with evidence: {with_evidence}/{len(records)}")
    print(f"Low-confidence rows flagged: {low_confidence}/{len(records)}")


if __name__ == "__main__":
    main()
