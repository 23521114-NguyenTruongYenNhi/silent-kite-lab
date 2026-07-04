from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


@dataclass(frozen=True)
class ArticleMeta:
    article_id: int
    title: str
    html_url: str
    updated_at: str


def slugify(title: str, article_id: int) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return f"{article_id}-{slug or 'article'}"


def clean_article_html(body: str, article_url_to_slug: dict[str, str]) -> str:
    soup = BeautifulSoup(body or "", "html.parser")

    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    for tag in soup.find_all("span"):
        tag.unwrap()

    for tag in soup.find_all(True):
        attrs_to_keep = {}
        if tag.name == "a" and tag.get("href"):
            attrs_to_keep["href"] = _normalize_href(tag["href"], article_url_to_slug)
        if tag.name == "img" and tag.get("src"):
            attrs_to_keep["src"] = tag["src"]
            if tag.get("alt"):
                attrs_to_keep["alt"] = tag["alt"]
        if tag.name in {"td", "th"} and tag.get("colspan"):
            attrs_to_keep["colspan"] = tag["colspan"]
        tag.attrs = attrs_to_keep

    markdown = html_to_markdown(
        str(soup),
        heading_style="ATX",
        bullets="-",
        convert=["a", "blockquote", "br", "code", "em", "h1", "h2", "h3", "h4", "h5", "h6",
                 "hr", "img", "li", "ol", "p", "pre", "strong", "table", "td", "th", "tr", "ul"],
    )
    markdown = unescape(markdown).replace("\xa0", " ")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    return markdown.strip()


def render_markdown(meta: ArticleMeta, body: str, article_url_to_slug: dict[str, str]) -> str:
    cleaned = clean_article_html(body, article_url_to_slug)
    title = meta.title.strip()
    return (
        f"# {title}\n\n"
        f"Article URL: {meta.html_url}\n\n"
        f"Updated: {meta.updated_at}\n\n"
        f"{cleaned}\n"
    )


def _normalize_href(href: str, article_url_to_slug: dict[str, str]) -> str:
    href = href.strip()
    if href.startswith("#") or href.startswith("mailto:"):
        return href

    parsed = urlparse(href)
    if parsed.netloc and "support.optisigns.com" not in parsed.netloc:
        return href

    url_without_fragment = href.split("#", 1)[0].rstrip("/")
    slug = article_url_to_slug.get(url_without_fragment)
    if not slug:
        return href

    fragment = f"#{href.split('#', 1)[1]}" if "#" in href else ""
    return f"./{slug}.md{fragment}"
