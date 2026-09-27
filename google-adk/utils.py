import re
import unicodedata

from google.genai import types


def text_content(content: types.Content | None) -> str:
    if content is None:
        return ""
    return "".join(
        part.text for part in content.parts or [] if part.text and not part.thought
    ).strip()


def one_line(text: str) -> str:
    """Collapse whitespace and limit a console detail to 120 characters."""
    collapsed = " ".join(text.split())
    return collapsed[:120] + "…" if len(collapsed) > 120 else collapsed


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def title_slug(story: str) -> str:
    """Make a safe, short filename component from the Product Owner's title."""
    match = re.search(r"^Title:[ \t]*(.*)$", story, flags=re.MULTILINE)
    title = match.group(1) if match else ""
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60].rstrip("-") or "specification"


def validate_headings(document: str, template: str) -> None:
    """Reject missing, reordered, duplicate or additional level-two headings."""
    expected = [line for line in template.splitlines() if line.startswith("## ")]
    actual = [line for line in document.splitlines() if line.startswith("## ")]
    for index, heading in enumerate(expected):
        if index >= len(actual) or actual[index] != heading:
            raise RuntimeError(f"Missing or reordered specification heading: {heading}")
    if len(actual) > len(expected):
        raise RuntimeError(f"Unexpected specification heading: {actual[len(expected)]}")
    if not document.startswith("# Specification:"):
        raise RuntimeError("The specification must start with '# Specification:'.")
