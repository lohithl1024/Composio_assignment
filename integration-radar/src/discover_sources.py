import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import HttpUrl

from src.models.app_record import AppResearchRecord, DiscoveredSource
from src.models.enums import ResearchStatus


DEFAULT_INPUT = Path("data/processed/app_records.stub.jsonl")
DEFAULT_OUTPUT = Path("data/processed/app_records.discovered.jsonl")


URL_FIELDS = (
    "official_site",
    "developer_docs",
    "api_docs",
    "auth_docs",
    "pricing_or_access",
    "mcp_url",
)


SOURCE_SEEDS: dict[str, dict[str, str | list[str]]] = {
    "salesforce": {
        "developer_docs": "https://developer.salesforce.com/docs",
        "api_docs": "https://developer.salesforce.com/docs/apis",
        "auth_docs": "https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_flows.htm&type=5",
        "pricing_or_access": "https://developer.salesforce.com/signup",
    },
    "hubspot": {
        "official_site": "https://www.hubspot.com/",
        "developer_docs": "https://developers.hubspot.com/",
        "api_docs": "https://developers.hubspot.com/docs/api/overview",
        "auth_docs": "https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication",
        "pricing_or_access": "https://developers.hubspot.com/docs/api/private-apps",
    },
    "pipedrive": {
        "developer_docs": "https://developers.pipedrive.com/docs/api/v1",
        "api_docs": "https://developers.pipedrive.com/docs/api/v1",
        "auth_docs": "https://pipedrive.readme.io/docs/marketplace-oauth-authorization",
    },
    "attio": {
        "developer_docs": "https://docs.attio.com/",
        "api_docs": "https://docs.attio.com/rest-api/overview",
        "auth_docs": "https://docs.attio.com/rest-api/authentication",
    },
    "twenty": {
        "developer_docs": "https://twenty.com/developers",
        "api_docs": "https://twenty.com/developers/rest-api",
        "auth_docs": "https://twenty.com/developers/section/authentication",
        "additional_source_urls": ["https://github.com/twentyhq/twenty"],
    },
    "podio": {
        "developer_docs": "https://developers.podio.com/",
        "api_docs": "https://developers.podio.com/doc",
        "auth_docs": "https://developers.podio.com/authentication",
    },
    "zoho_crm": {
        "developer_docs": "https://www.zoho.com/crm/developer/docs/",
        "api_docs": "https://www.zoho.com/crm/developer/docs/api/v8/",
        "auth_docs": "https://www.zoho.com/accounts/protocol/oauth.html",
    },
    "close": {
        "developer_docs": "https://developer.close.com/",
        "api_docs": "https://developer.close.com/",
        "auth_docs": "https://developer.close.com/topics/authentication/",
    },
    "copper": {
        "developer_docs": "https://developer.copper.com/",
        "api_docs": "https://developer.copper.com/",
    },
    "dealcloud": {
        "developer_docs": "https://api.docs.dealcloud.com/",
        "api_docs": "https://api.docs.dealcloud.com/",
    },
    "zendesk": {
        "developer_docs": "https://developer.zendesk.com/",
        "api_docs": "https://developer.zendesk.com/api-reference/",
        "auth_docs": "https://developer.zendesk.com/documentation/api-basics/authentication/",
    },
    "intercom": {
        "developer_docs": "https://developers.intercom.com/",
        "api_docs": "https://developers.intercom.com/docs/references/rest-api/api.intercom.io/",
        "auth_docs": "https://developers.intercom.com/docs/build-an-integration/learn-more/authentication/",
    },
    "freshdesk": {
        "developer_docs": "https://developers.freshdesk.com/",
        "api_docs": "https://developers.freshdesk.com/api/",
    },
    "front": {
        "developer_docs": "https://dev.frontapp.com/",
        "api_docs": "https://dev.frontapp.com/reference/introduction",
        "auth_docs": "https://dev.frontapp.com/docs/oauth",
    },
    "pylon": {
        "developer_docs": "https://docs.usepylon.com/",
        "api_docs": "https://docs.usepylon.com/reference",
    },
    "liveagent": {
        "developer_docs": "https://support.liveagent.com/061754-API",
        "api_docs": "https://support.liveagent.com/061754-API",
    },
    "plain": {
        "developer_docs": "https://www.plain.com/docs",
        "api_docs": "https://www.plain.com/docs/api-reference",
    },
    "help_scout": {
        "developer_docs": "https://developer.helpscout.com/",
        "api_docs": "https://developer.helpscout.com/mailbox-api/",
        "auth_docs": "https://developer.helpscout.com/mailbox-api/overview/authentication/",
    },
    "gorgias": {
        "developer_docs": "https://developers.gorgias.com/",
        "api_docs": "https://developers.gorgias.com/reference/introduction",
    },
    "gladly": {
        "developer_docs": "https://developer.gladly.com/",
        "api_docs": "https://developer.gladly.com/rest/",
    },
    "slack": {
        "developer_docs": "https://api.slack.com/",
        "api_docs": "https://api.slack.com/web",
        "auth_docs": "https://api.slack.com/authentication",
    },
    "twilio": {
        "developer_docs": "https://www.twilio.com/docs",
        "api_docs": "https://www.twilio.com/docs/usage/api",
        "auth_docs": "https://www.twilio.com/docs/iam/api",
    },
    "zoho_cliq": {
        "developer_docs": "https://www.zoho.com/cliq/help/restapi/v2/",
        "api_docs": "https://www.zoho.com/cliq/help/restapi/v2/",
    },
    "lark_larksuite": {
        "developer_docs": "https://open.larksuite.com/",
        "api_docs": "https://open.larksuite.com/document/home/index",
    },
    "discord": {
        "developer_docs": "https://discord.com/developers/docs/intro",
        "api_docs": "https://discord.com/developers/docs/reference",
        "auth_docs": "https://discord.com/developers/docs/topics/oauth2",
    },
    "telegram": {
        "developer_docs": "https://core.telegram.org/",
        "api_docs": "https://core.telegram.org/api",
        "auth_docs": "https://core.telegram.org/bots/api",
    },
    "whatsapp_business": {
        "developer_docs": "https://developers.facebook.com/docs/whatsapp",
        "api_docs": "https://developers.facebook.com/docs/whatsapp/cloud-api",
        "auth_docs": "https://developers.facebook.com/docs/facebook-login/guides/access-tokens",
    },
    "aircall": {
        "developer_docs": "https://developer.aircall.io/",
        "api_docs": "https://developer.aircall.io/api-references/",
    },
    "vonage": {
        "developer_docs": "https://developer.vonage.com/",
        "api_docs": "https://developer.vonage.com/en/api",
    },
    "google_ads": {
        "developer_docs": "https://developers.google.com/google-ads/api/docs/start",
        "api_docs": "https://developers.google.com/google-ads/api/reference/rpc",
        "auth_docs": "https://developers.google.com/google-ads/api/docs/oauth/overview",
        "pricing_or_access": "https://developers.google.com/google-ads/api/docs/access-levels",
    },
    "meta_ads": {
        "developer_docs": "https://developers.facebook.com/docs/marketing-apis/",
        "api_docs": "https://developers.facebook.com/docs/marketing-api/reference",
        "auth_docs": "https://developers.facebook.com/docs/facebook-login/guides/access-tokens",
        "pricing_or_access": "https://developers.facebook.com/docs/development/release/business-verification",
    },
    "linkedin_ads": {
        "developer_docs": "https://learn.microsoft.com/linkedin/marketing/",
        "api_docs": "https://learn.microsoft.com/linkedin/marketing/integrations/ads/",
        "auth_docs": "https://learn.microsoft.com/linkedin/shared/authentication/authentication",
    },
    "gohighlevel": {
        "developer_docs": "https://highlevel.stoplight.io/",
        "api_docs": "https://highlevel.stoplight.io/docs/integrations/",
    },
    "mailchimp": {
        "developer_docs": "https://mailchimp.com/developer/",
        "api_docs": "https://mailchimp.com/developer/marketing/api/",
        "auth_docs": "https://mailchimp.com/developer/marketing/guides/access-user-data-oauth-2/",
    },
    "klaviyo": {
        "developer_docs": "https://developers.klaviyo.com/",
        "api_docs": "https://developers.klaviyo.com/en/reference/api_overview",
        "auth_docs": "https://developers.klaviyo.com/en/docs/authenticate_",
    },
    "pinterest": {
        "developer_docs": "https://developers.pinterest.com/",
        "api_docs": "https://developers.pinterest.com/docs/api/v5/",
        "auth_docs": "https://developers.pinterest.com/docs/getting-started/authentication/",
    },
    "threads_meta": {
        "developer_docs": "https://developers.facebook.com/docs/threads",
        "api_docs": "https://developers.facebook.com/docs/threads/reference",
    },
    "sendgrid": {
        "developer_docs": "https://www.twilio.com/docs/sendgrid",
        "api_docs": "https://www.twilio.com/docs/sendgrid/api-reference",
        "auth_docs": "https://www.twilio.com/docs/sendgrid/api-reference/how-to-use-the-sendgrid-v3-api/authentication",
    },
    "shopify": {
        "developer_docs": "https://shopify.dev/docs",
        "api_docs": "https://shopify.dev/docs/api",
        "auth_docs": "https://shopify.dev/docs/apps/build/authentication-authorization",
    },
    "woocommerce": {
        "developer_docs": "https://woocommerce.com/document/woocommerce-rest-api/",
        "api_docs": "https://woocommerce.github.io/woocommerce-rest-api-docs/",
    },
    "bigcommerce": {
        "developer_docs": "https://developer.bigcommerce.com/",
        "api_docs": "https://developer.bigcommerce.com/docs/rest-management",
    },
    "salesforce_commerce_cloud": {
        "developer_docs": "https://developer.salesforce.com/docs/commerce",
        "api_docs": "https://developer.salesforce.com/docs/commerce/commerce-api",
    },
    "magento_adobe_commerce": {
        "developer_docs": "https://developer.adobe.com/commerce/",
        "api_docs": "https://developer.adobe.com/commerce/webapi/rest/",
        "auth_docs": "https://developer.adobe.com/commerce/webapi/get-started/authentication/",
    },
    "squarespace": {
        "developer_docs": "https://developers.squarespace.com/",
        "api_docs": "https://developers.squarespace.com/commerce-apis",
    },
    "ecwid": {
        "developer_docs": "https://api-docs.ecwid.com/",
        "api_docs": "https://api-docs.ecwid.com/reference/rest-api",
    },
    "gumroad": {
        "developer_docs": "https://gumroad.com/api",
        "api_docs": "https://gumroad.com/api",
    },
    "amazon_selling_partner": {
        "developer_docs": "https://developer-docs.amazon.com/sp-api/",
        "api_docs": "https://developer-docs.amazon.com/sp-api/reference/welcome",
    },
    "dataforseo": {
        "developer_docs": "https://docs.dataforseo.com/",
        "api_docs": "https://docs.dataforseo.com/",
    },
    "se_ranking": {
        "developer_docs": "https://seranking.com/api.html",
        "api_docs": "https://seranking.com/api.html",
    },
    "ahrefs": {
        "developer_docs": "https://docs.ahrefs.com/",
        "api_docs": "https://docs.ahrefs.com/",
        "pricing_or_access": "https://ahrefs.com/api",
    },
    "mrscraper": {
        "developer_docs": "https://docs.mrscraper.com/",
        "api_docs": "https://docs.mrscraper.com/",
    },
    "apify": {
        "developer_docs": "https://docs.apify.com/",
        "api_docs": "https://docs.apify.com/api/v2",
        "auth_docs": "https://docs.apify.com/platform/integrations/api",
    },
    "firecrawl": {
        "developer_docs": "https://docs.firecrawl.dev/",
        "api_docs": "https://docs.firecrawl.dev/api-reference/introduction",
    },
    "bright_data": {
        "developer_docs": "https://docs.brightdata.com/",
        "api_docs": "https://docs.brightdata.com/api-reference/introduction",
    },
    "sherlock": {
        "developer_docs": "https://github.com/sherlock-project/sherlock",
        "api_docs": "https://github.com/sherlock-project/sherlock",
        "additional_source_urls": ["https://sherlock-project.github.io/"],
    },
    "github": {
        "developer_docs": "https://docs.github.com/rest",
        "api_docs": "https://docs.github.com/rest",
        "auth_docs": "https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps",
    },
    "vercel": {
        "developer_docs": "https://vercel.com/docs/rest-api",
        "api_docs": "https://vercel.com/docs/rest-api",
        "auth_docs": "https://vercel.com/docs/rest-api/reference/authentication",
    },
    "netlify": {
        "developer_docs": "https://docs.netlify.com/api/get-started/",
        "api_docs": "https://open-api.netlify.com/",
    },
    "cloudflare": {
        "developer_docs": "https://developers.cloudflare.com/api/",
        "api_docs": "https://developers.cloudflare.com/api/",
    },
    "supabase": {
        "developer_docs": "https://supabase.com/docs",
        "api_docs": "https://supabase.com/docs/reference",
    },
    "neo4j": {
        "developer_docs": "https://neo4j.com/docs/api/",
        "api_docs": "https://neo4j.com/docs/api/",
    },
    "snowflake": {
        "developer_docs": "https://docs.snowflake.com/",
        "api_docs": "https://docs.snowflake.com/en/developer-guide/snowflake-rest-api/snowflake-rest-api",
    },
    "mongodb_atlas": {
        "developer_docs": "https://www.mongodb.com/docs/atlas/api/",
        "api_docs": "https://www.mongodb.com/docs/atlas/api/",
    },
    "datadog": {
        "developer_docs": "https://docs.datadoghq.com/api/",
        "api_docs": "https://docs.datadoghq.com/api/latest/",
    },
    "sentry": {
        "developer_docs": "https://docs.sentry.io/api/",
        "api_docs": "https://docs.sentry.io/api/",
        "auth_docs": "https://docs.sentry.io/api/auth/",
    },
    "notion": {
        "developer_docs": "https://developers.notion.com/",
        "api_docs": "https://developers.notion.com/reference/intro",
        "auth_docs": "https://developers.notion.com/docs/authorization",
    },
    "airtable": {
        "developer_docs": "https://airtable.com/developers",
        "api_docs": "https://airtable.com/developers/web/api/introduction",
        "auth_docs": "https://airtable.com/developers/web/guides/oauth-integrations",
    },
    "linear": {
        "developer_docs": "https://developers.linear.app/",
        "api_docs": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        "auth_docs": "https://developers.linear.app/docs/oauth/authentication",
    },
    "jira": {
        "developer_docs": "https://developer.atlassian.com/",
        "api_docs": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/",
        "auth_docs": "https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/",
    },
    "asana": {
        "developer_docs": "https://developers.asana.com/docs",
        "api_docs": "https://developers.asana.com/reference/rest-api-reference",
        "auth_docs": "https://developers.asana.com/docs/oauth",
    },
    "monday_com": {
        "developer_docs": "https://developer.monday.com/",
        "api_docs": "https://developer.monday.com/api-reference/docs",
        "auth_docs": "https://developer.monday.com/apps/docs/oauth",
    },
    "clickup": {
        "developer_docs": "https://clickup.com/api",
        "api_docs": "https://clickup.com/api",
    },
    "coda": {
        "developer_docs": "https://coda.io/developers",
        "api_docs": "https://coda.io/developers/apis/v1",
    },
    "smartsheet": {
        "developer_docs": "https://smartsheet.redoc.ly/",
        "api_docs": "https://smartsheet.redoc.ly/",
    },
    "harvest": {
        "developer_docs": "https://help.getharvest.com/api-v2/",
        "api_docs": "https://help.getharvest.com/api-v2/",
        "auth_docs": "https://help.getharvest.com/api-v2/authentication-api/authentication/authentication/",
    },
    "stripe": {
        "developer_docs": "https://docs.stripe.com/",
        "api_docs": "https://docs.stripe.com/api",
        "auth_docs": "https://docs.stripe.com/keys",
    },
    "plaid": {
        "developer_docs": "https://plaid.com/docs/",
        "api_docs": "https://plaid.com/docs/api/",
        "auth_docs": "https://plaid.com/docs/api/tokens/",
    },
    "binance": {
        "developer_docs": "https://developers.binance.com/docs",
        "api_docs": "https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-api-information",
    },
    "quickbooks": {
        "developer_docs": "https://developer.intuit.com/app/developer/qbo/docs/get-started",
        "api_docs": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account",
        "auth_docs": "https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization",
    },
    "xero": {
        "developer_docs": "https://developer.xero.com/documentation/",
        "api_docs": "https://developer.xero.com/documentation/api/accounting/overview",
        "auth_docs": "https://developer.xero.com/documentation/guides/oauth2/overview",
    },
    "brex": {
        "developer_docs": "https://developer.brex.com/",
        "api_docs": "https://developer.brex.com/openapi",
    },
    "ramp": {
        "developer_docs": "https://docs.ramp.com/",
        "api_docs": "https://docs.ramp.com/developer-api/v1/overview/introduction",
    },
    "ipayx": {
        "developer_docs": "https://ipayx.ai/docs",
        "api_docs": "https://ipayx.ai/docs",
    },
    "notebooklm": {
        "developer_docs": "https://cloud.google.com/gemini",
        "api_docs": "https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini",
    },
    "otter_ai": {
        "developer_docs": "https://help.otter.ai/",
        "mcp_url": "https://help.otter.ai/hc/en-us/articles/40159228153751-Otter-MCP-Server",
    },
    "devin": {
        "developer_docs": "https://docs.devin.ai/",
        "api_docs": "https://docs.devin.ai/api-reference/overview",
        "mcp_url": "https://docs.devin.ai/integrations/mcp",
    },
    "mermaid_cli": {
        "developer_docs": "https://github.com/mermaid-js/mermaid-cli",
        "api_docs": "https://github.com/mermaid-js/mermaid-cli",
    },
    "youtube_transcript": {
        "developer_docs": "https://transcriptapi.com/",
        "api_docs": "https://transcriptapi.com/docs",
    },
}


def load_jsonl(path: Path) -> list[AppResearchRecord]:
    with path.open(encoding="utf-8") as file:
        return [AppResearchRecord.model_validate_json(line) for line in file if line.strip()]


def write_jsonl(records: list[AppResearchRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(record.model_dump_json() + "\n")


def ensure_url(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def base_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2] in {"co", "com", "org", "net"} and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def official_site_from_hint(website_hint: str) -> str | None:
    if " " in website_hint:
        return None
    url = ensure_url(website_hint)
    parsed = urlparse(url)
    if not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    docs_prefixes = (
        "api.",
        "api-docs.",
        "developer.",
        "developers.",
        "docs.",
        "help.",
        "learn.",
        "open.",
        "core.",
    )
    docs_hosts = {
        "shopify.dev",
        "firecrawl.dev",
        "developers.linear.app",
        "github.com",
        "developer-docs.amazon.com",
    }
    if host in docs_hosts or host.startswith(docs_prefixes):
        host = base_domain(host)
    return f"https://{host}/"


def add_source(
    sources: list[DiscoveredSource],
    source_type: str,
    url: str,
    title: str | None,
    method: str,
    is_official: bool = True,
) -> None:
    normalized_url = ensure_url(url)
    if not normalized_url:
        return
    if any(str(source.url).rstrip("/") == normalized_url.rstrip("/") for source in sources):
        return
    sources.append(
        DiscoveredSource(
            source_type=source_type,
            url=normalized_url,
            title=title,
            is_official=is_official,
            discovery_method=method,
        )
    )


def discover_sources_for_record(record: AppResearchRecord) -> AppResearchRecord:
    seed = SOURCE_SEEDS.get(record.app_slug, {})
    discovered: list[DiscoveredSource] = []

    official_site = str(seed.get("official_site") or official_site_from_hint(record.website_hint) or "")
    if official_site:
        record.sources.official_site = HttpUrl(official_site)
        add_source(discovered, "official_site", official_site, f"{record.app_name} official site", "deterministic_hint")

    for field_name in ("developer_docs", "api_docs", "auth_docs", "pricing_or_access", "mcp_url"):
        value = seed.get(field_name)
        if not isinstance(value, str) or not value:
            continue
        setattr(record.sources, field_name, HttpUrl(ensure_url(value)))
        add_source(
            discovered,
            field_name,
            value,
            f"{record.app_name} {field_name.replace('_', ' ')}",
            "manual_seed",
        )

    additional_urls = seed.get("additional_source_urls", [])
    if isinstance(additional_urls, list):
        for url in additional_urls:
            if isinstance(url, str) and url:
                record.sources.additional_source_urls.append(HttpUrl(ensure_url(url)))
                add_source(discovered, "additional", url, f"{record.app_name} supporting source", "manual_seed")

    if record.sources.mcp_url:
        record.sources.mcp_evidence = [record.sources.mcp_url]

    record.sources.discovered_sources = discovered
    record.workflow.source_count = len(discovered)
    record.workflow.research_status = ResearchStatus.DISCOVERED
    record.agent_notes = append_agent_note(
        record.agent_notes,
        f"discover_sources.py attached {len(discovered)} source URL(s); no auth/buildability extraction performed.",
    )
    return record


def append_agent_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    return f"{existing}\n{note}"


def discover_sources(input_path: Path, output_path: Path) -> list[AppResearchRecord]:
    records = load_jsonl(input_path)
    discovered_records = [discover_sources_for_record(record) for record in records]
    write_jsonl(discovered_records, output_path)
    return discovered_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attach official source URLs to stub app records without classifying fields."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = discover_sources(args.input, args.output)
    with_docs = sum(1 for record in records if record.sources.developer_docs or record.sources.api_docs)
    print(f"Wrote {len(records)} discovered records to {args.output}")
    print(f"Records with developer/API docs: {with_docs}/{len(records)}")


if __name__ == "__main__":
    main()
