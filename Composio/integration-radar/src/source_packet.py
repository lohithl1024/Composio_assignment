from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

from src.models.app_record import AppResearchRecord, DiscoveredSource


MAX_SOURCES_PER_APP = 6
MAX_SNIPPET_CHARS = 1200


@dataclass
class SourceSnippet:
    source_type: str
    url: str
    title: str | None
    snippet: str
    fetched: bool
    error: str | None = None


@dataclass
class ResearchPacket:
    app_name: str
    category: str
    website_hint: str
    sources: list[SourceSnippet]


def build_source_packet(record: AppResearchRecord, fetch: bool = False) -> ResearchPacket:
    sources = prioritized_sources(record.sources.discovered_sources)
    snippets = [build_source_snippet(source, fetch=fetch) for source in sources]
    return ResearchPacket(
        app_name=record.app_name,
        category=record.category.value,
        website_hint=record.website_hint,
        sources=snippets,
    )


def prioritized_sources(sources: Iterable[DiscoveredSource]) -> list[DiscoveredSource]:
    priority = {
        "developer_docs": 0,
        "api_docs": 1,
        "auth_docs": 2,
        "pricing_or_access": 3,
        "mcp_url": 4,
        "mcp": 4,
        "official_site": 5,
        "additional": 6,
    }
    return sorted(sources, key=lambda source: priority.get(source.source_type, 99))[:MAX_SOURCES_PER_APP]


def build_source_snippet(source: DiscoveredSource, fetch: bool = False) -> SourceSnippet:
    fallback = fallback_snippet(source)
    if not fetch:
        return SourceSnippet(
            source_type=source.source_type,
            url=str(source.url),
            title=source.title,
            snippet=fallback,
            fetched=False,
        )

    try:
        html = fetch_url_text(str(source.url))
        snippet = compact_text(html) or fallback
        return SourceSnippet(
            source_type=source.source_type,
            url=str(source.url),
            title=source.title,
            snippet=snippet[:MAX_SNIPPET_CHARS],
            fetched=True,
        )
    except Exception as exc:  # noqa: BLE001 - one bad page should not stop extraction.
        return SourceSnippet(
            source_type=source.source_type,
            url=str(source.url),
            title=source.title,
            snippet=fallback,
            fetched=False,
            error=str(exc),
        )


def fetch_url_text(url: str) -> str:
    headers = {
        "User-Agent": "IntegrationRadar/0.1 (+research pipeline; source discovery)",
    }
    with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def compact_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    if title and title not in text[:200]:
        text = f"{title}. {text}"
    return text[:MAX_SNIPPET_CHARS]


def fallback_snippet(source: DiscoveredSource) -> str:
    title = source.title or source.source_type.replace("_", " ")
    return (
        f"{title}. Source discovered as {source.source_type} via "
        f"{source.discovery_method}. URL: {source.url}"
    )
