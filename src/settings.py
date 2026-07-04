from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _truthy(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean_env(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(frozen=True)
class Settings:
    base_url: str
    locale: str
    article_limit: int
    request_timeout_seconds: int
    data_dir: Path
    markdown_dir: Path
    state_path: Path
    upload_state_path: Path
    upload_to_openai: bool
    force_upload_all: bool
    create_assistant_if_missing: bool
    openai_api_key: str | None
    openai_vector_store_id: str | None
    openai_assistant_id: str | None
    openai_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        return cls(
            base_url=os.getenv("HELP_CENTER_BASE_URL", "https://support.optisigns.com").rstrip("/"),
            locale=os.getenv("HELP_CENTER_LOCALE", "en-us"),
            article_limit=int(os.getenv("ARTICLE_LIMIT", "50")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
            data_dir=data_dir,
            markdown_dir=data_dir / "articles",
            state_path=data_dir / "state.json",
            upload_state_path=data_dir / "upload_state.json",
            upload_to_openai=_truthy(os.getenv("UPLOAD_TO_OPENAI"), True),
            force_upload_all=_truthy(os.getenv("FORCE_UPLOAD_ALL"), False),
            create_assistant_if_missing=_truthy(os.getenv("CREATE_ASSISTANT_IF_MISSING"), True),
            openai_api_key=_clean_env(os.getenv("OPENAI_API_KEY")) or _clean_env(os.getenv("API_KEY")),
            openai_vector_store_id=_clean_env(os.getenv("OPENAI_VECTOR_STORE_ID")),
            openai_assistant_id=_clean_env(os.getenv("OPENAI_ASSISTANT_ID")),
            openai_model=_clean_env(os.getenv("OPENAI_MODEL")) or "gpt-4.1-mini",
        )
