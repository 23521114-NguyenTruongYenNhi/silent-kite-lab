from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.assistant import create_or_update_assistant
from src.scraper import scrape_articles
from src.settings import Settings
from src.uploader import upload_changed_files


def configure_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/last_run.log", encoding="utf-8"),
        ],
    )


def main() -> int:
    load_dotenv()
    configure_logging()
    settings = Settings.from_env()
    logger = logging.getLogger("main")

    scrape_result = scrape_articles(settings)
    upload_summary = {"uploaded": 0, "vector_store_id": os.getenv("OPENAI_VECTOR_STORE_ID", "")}

    if settings.upload_to_openai:
        files_to_upload = scrape_result.changed_files
        if settings.force_upload_all:
            files_to_upload = sorted(settings.markdown_dir.glob("*.md"))
            logger.info("FORCE_UPLOAD_ALL=true, uploading all %s Markdown files", len(files_to_upload))
        upload_summary = upload_changed_files(settings, files_to_upload)
        vector_store_id = upload_summary.get("vector_store_id")
        if vector_store_id and (settings.openai_assistant_id or settings.create_assistant_if_missing):
            assistant_summary = create_or_update_assistant(settings, vector_store_id)
            upload_summary.update(assistant_summary)
    else:
        logger.info("UPLOAD_TO_OPENAI=false, skipping vector store upload")

    summary = {
        "scrape": scrape_result.to_dict(),
        "upload": upload_summary,
    }
    Path("logs").mkdir(exist_ok=True)
    Path("logs/last_run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Run summary: %s", json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
