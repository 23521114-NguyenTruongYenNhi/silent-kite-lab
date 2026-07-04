from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from src.cleaner import ArticleMeta, render_markdown, slugify
from src.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapeResult:
    total_seen: int
    added: int
    updated: int
    skipped: int
    changed_files: list[Path]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_seen": self.total_seen,
            "added": self.added,
            "updated": self.updated,
            "skipped": self.skipped,
            "changed_files": [str(path) for path in self.changed_files],
        }


def scrape_articles(settings: Settings) -> ScrapeResult:
    settings.markdown_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(settings.state_path)
    articles = _fetch_articles(settings)
    article_url_to_slug = {
        article["html_url"].rstrip("/"): slugify(article["title"], article["id"])
        for article in articles
    }

    added = updated = skipped = 0
    changed_files: list[Path] = []
    next_state = dict(state)

    for article in articles:
        meta = ArticleMeta(
            article_id=article["id"],
            title=article["title"],
            html_url=article["html_url"],
            updated_at=article.get("updated_at", ""),
        )
        slug = slugify(meta.title, meta.article_id)
        markdown = render_markdown(meta, article.get("body", ""), article_url_to_slug)
        digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        previous = state.get(str(meta.article_id), {})
        file_path = settings.markdown_dir / f"{slug}.md"

        if previous.get("hash") == digest and file_path.exists():
            skipped += 1
        else:
            if previous:
                updated += 1
            else:
                added += 1
            file_path.write_text(markdown, encoding="utf-8")
            changed_files.append(file_path)

        next_state[str(meta.article_id)] = {
            "title": meta.title,
            "url": meta.html_url,
            "updated_at": meta.updated_at,
            "slug": slug,
            "hash": digest,
            "path": str(file_path),
        }

    settings.state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.state_path.write_text(json.dumps(next_state, indent=2), encoding="utf-8")
    logger.info("Scraped %s articles: %s added, %s updated, %s skipped", len(articles), added, updated, skipped)
    return ScrapeResult(len(articles), added, updated, skipped, changed_files)


def _fetch_articles(settings: Settings) -> list[dict[str, Any]]:
    url = f"{settings.base_url}/api/v2/help_center/{settings.locale}/articles.json"
    params = {"per_page": 100, "sort_by": "updated_at", "sort_order": "desc"}
    articles: list[dict[str, Any]] = []

    while url and len(articles) < settings.article_limit:
        response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        page_articles = [article for article in payload.get("articles", []) if not article.get("draft")]
        articles.extend(page_articles)
        url = payload.get("next_page")
        params = None

    return articles[: settings.article_limit]


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
