from __future__ import annotations

import logging
import json
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.settings import Settings

logger = logging.getLogger(__name__)

CHUNKING_STRATEGY = {
    "type": "static",
    "static": {
        "max_chunk_size_tokens": 800,
        "chunk_overlap_tokens": 160,
    },
}


def upload_changed_files(settings: Settings, files: list[Path]) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when UPLOAD_TO_OPENAI=true")

    client = OpenAI(api_key=settings.openai_api_key)
    vector_store_id = settings.openai_vector_store_id or _create_vector_store(client)
    upload_state = _load_upload_state(settings.upload_state_path)
    uploaded = 0
    estimated_chunks = 0

    for file_path in files:
        state_key = str(file_path)
        previous = upload_state.get(state_key, {})
        _remove_previous_file(client, vector_store_id, previous)

        estimated_chunks += estimate_chunks(file_path)
        logger.info("Uploading %s to vector store %s", file_path, vector_store_id)
        with file_path.open("rb") as handle:
            uploaded_file = client.files.create(file=handle, purpose="assistants")
        vector_file_id = _attach_file(client, vector_store_id, uploaded_file.id)
        upload_state[state_key] = {
            "openai_file_id": uploaded_file.id,
            "vector_store_file_id": vector_file_id,
        }
        uploaded += 1

    settings.upload_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.upload_state_path.write_text(json.dumps(upload_state, indent=2), encoding="utf-8")
    logger.info("Uploaded %s changed files, estimated %s chunks", uploaded, estimated_chunks)
    return {
        "vector_store_id": vector_store_id,
        "uploaded": uploaded,
        "estimated_chunks": estimated_chunks,
        "chunking": CHUNKING_STRATEGY,
    }


def estimate_chunks(file_path: Path) -> int:
    text = file_path.read_text(encoding="utf-8")
    approx_tokens = max(1, len(text) // 4)
    chunk_size = CHUNKING_STRATEGY["static"]["max_chunk_size_tokens"]
    overlap = CHUNKING_STRATEGY["static"]["chunk_overlap_tokens"]
    stride = max(1, chunk_size - overlap)
    return max(1, 1 + max(0, approx_tokens - chunk_size) // stride)


def _create_vector_store(client: OpenAI) -> str:
    vector_store = client.vector_stores.create(name="OptiBot Mini Clone Docs")
    logger.info("Created vector store %s", vector_store.id)
    return vector_store.id


def _attach_file(client: OpenAI, vector_store_id: str, file_id: str) -> str:
    try:
        vector_file = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
            chunking_strategy=CHUNKING_STRATEGY,
        )
    except TypeError:
        logger.warning("Installed OpenAI SDK does not accept chunking_strategy; using server default chunking")
        vector_file = client.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_id)

    for _ in range(60):
        status = getattr(vector_file, "status", None)
        if status == "completed":
            return vector_file.id
        if status == "failed":
            raise RuntimeError(f"Vector store file {vector_file.id} failed to process")
        time.sleep(2)
        vector_file = client.vector_stores.files.retrieve(vector_store_id=vector_store_id, file_id=vector_file.id)

    raise TimeoutError(f"Timed out waiting for vector store file {vector_file.id}")


def _load_upload_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _remove_previous_file(client: OpenAI, vector_store_id: str, previous: dict[str, Any]) -> None:
    vector_file_id = previous.get("vector_store_file_id")
    openai_file_id = previous.get("openai_file_id")
    if vector_file_id:
        try:
            client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=vector_file_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not remove previous vector file %s: %s", vector_file_id, exc)
    if openai_file_id:
        try:
            client.files.delete(openai_file_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not delete previous OpenAI file %s: %s", openai_file_id, exc)
