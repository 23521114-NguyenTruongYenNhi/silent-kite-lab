from __future__ import annotations

from typing import Any

from openai import OpenAI

from src.settings import Settings


SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


def create_or_update_assistant(settings: Settings, vector_store_id: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = OpenAI(api_key=settings.openai_api_key)
    tool_resources = {"file_search": {"vector_store_ids": [vector_store_id]}}

    if settings.openai_assistant_id:
        assistant = client.beta.assistants.update(
            assistant_id=settings.openai_assistant_id,
            instructions=SYSTEM_PROMPT,
            tools=[{"type": "file_search"}],
            tool_resources=tool_resources,
            model=settings.openai_model,
        )
    else:
        assistant = client.beta.assistants.create(
            name="OptiBot Mini Clone",
            instructions=SYSTEM_PROMPT,
            tools=[{"type": "file_search"}],
            tool_resources=tool_resources,
            model=settings.openai_model,
        )

    return {"assistant_id": assistant.id}
