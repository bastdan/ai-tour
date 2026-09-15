from collections.abc import Mapping
from datetime import date

from google.genai import types


def has_http_scheme(url: str) -> bool:
    """Check for an HTTP(S) prefix without validating the full URL."""
    return url.startswith(("https://", "http://"))


def text_content(content: types.Content | None) -> str:
    if content is None:
        return ""
    return "".join(
        part.text for part in content.parts or [] if part.text and not part.thought
    ).strip()


def grounding_sources(metadata: types.GroundingMetadata | None) -> dict[str, str]:
    sources: dict[str, str] = {}
    if metadata:
        for chunk in metadata.grounding_chunks or []:
            if chunk.web and chunk.web.uri:
                url = chunk.web.uri
                if has_http_scheme(url):
                    sources[url] = chunk.web.title or url
    return sources


def format_source_links(sources: Mapping[str, str]) -> str:
    """Format source links as Markdown bullets in mapping order."""
    return "\n".join(f"- [{title}]({url})" for url, title in sources.items())


def parse_iso_date(value: str) -> date:
    """Parse a date in strict YYYY-MM-DD format."""
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Use YYYY-MM-DD.")
    return parsed
