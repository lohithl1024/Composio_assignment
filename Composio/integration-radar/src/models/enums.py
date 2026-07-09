from enum import Enum


class AppCategory(str, Enum):
    CRM_AND_SALES = "CRM and Sales"
    SUPPORT_AND_HELPDESK = "Support and Helpdesk"
    COMMUNICATIONS_AND_MESSAGING = "Communications and Messaging"
    MARKETING_ADS_EMAIL_SOCIAL = "Marketing, Ads, Email and Social"
    ECOMMERCE = "Ecommerce"
    DATA_SEO_SCRAPING = "Data, SEO and Scraping"
    DEVELOPER_INFRA_DATA = "Developer, Infra and Data platforms"
    PRODUCTIVITY_PROJECT_MANAGEMENT = "Productivity and Project Management"
    FINANCE_FINTECH = "Finance and Fintech"
    AI_RESEARCH_MEDIA = "AI, Research and Media-native"


class SourceType(str, Enum):
    OFFICIAL_DOCS = "official_docs"
    OFFICIAL_BLOG_OR_HELP = "official_blog_or_help"
    PRICING_OR_ACCESS_PAGE = "pricing_or_access_page"
    DEVELOPER_PORTAL = "developer_portal"
    GITHUB_REPO = "github_repo"
    COMMUNITY_DOCS = "community_docs"
    THIRD_PARTY_ARTICLE = "third_party_article"
    UNKNOWN = "unknown"


class AccessModel(str, Enum):
    SELF_SERVE_FREE_OR_TRIAL = "self_serve_free_or_trial"
    SELF_SERVE_PAID_PLAN_REQUIRED = "self_serve_paid_plan_required"
    ADMIN_OR_WORKSPACE_DEPENDENT = "admin_or_workspace_dependent"
    PARTNER_OR_CONTACT_SALES_GATED = "partner_or_contact_sales_gated"
    UNCLEAR = "unclear"


class ApiBreadth(str, Enum):
    NONE_OR_UNCLEAR = "none_or_unclear"
    NARROW = "narrow"
    MODERATE = "moderate"
    BROAD = "broad"
    PLATFORM_LEVEL = "platform_level"


class ApiProtocol(str, Enum):
    REST = "REST"
    GRAPHQL = "GraphQL"
    SOAP = "SOAP"
    WEBHOOKS = "Webhooks"
    SDK_ONLY = "SDK-only"
    CLI = "CLI"
    MCP = "MCP"
    UNKNOWN = "unknown"


class AuthComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    UNCLEAR = "unclear"


class TernaryStatus(str, Enum):
    YES = "yes"
    NO = "no"
    SOMETIMES = "sometimes"
    LIMITED = "limited"
    UNCLEAR = "unclear"


class McpStatus(str, Enum):
    OFFICIAL = "official"
    COMMUNITY = "community"
    NONE_FOUND = "none_found"
    UNCLEAR = "unclear"


class BuildabilityVerdict(str, Enum):
    BUILDABLE_NOW = "buildable_now"
    BUILDABLE_WITH_CAVEATS = "buildable_with_caveats"
    POSSIBLE_BUT_GATED = "possible_but_gated"
    NOT_PRACTICAL_TODAY = "not_practical_today"
    UNCLEAR_NEEDS_REVIEW = "unclear_needs_review"


class BlockerType(str, Enum):
    NONE = "none"
    PARTNER_GATED_ACCESS = "partner_gated_access"
    CONTACT_SALES_REQUIRED = "contact_sales_required"
    PAID_PLAN_REQUIRED = "paid_plan_required"
    ADMIN_SETUP_REQUIRED = "admin_setup_required"
    NO_PUBLIC_API = "no_public_api"
    API_TOO_NARROW = "api_too_narrow"
    POOR_OR_FRAGMENTED_DOCS = "poor_or_fragmented_docs"
    NO_SANDBOX_OR_TEST_PATH = "no_sandbox_or_test_path"
    APP_REVIEW_OR_BUSINESS_VERIFICATION = "app_review_or_business_verification"
    UNCLEAR_ACCESS = "unclear_access"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchStatus(str, Enum):
    PENDING = "pending"
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"


class VerificationStatus(str, Enum):
    NOT_CHECKED = "not_checked"
    NOT_VERIFIED = "not_verified"
    AGENT_VERIFIED = "agent_verified"
    PASS = "pass"
    FLAGGED = "flagged"
    CORRECTED = "corrected"
    HUMAN_SAMPLED_VERIFIED = "human_sampled_verified"
    CORRECTED_AFTER_VERIFICATION = "corrected_after_verification"
    NEEDS_REVIEW = "needs_review"


class HumanReviewRequirement(str, Enum):
    NO = "no"
    YES = "yes"
    UNCLEAR = "unclear"
