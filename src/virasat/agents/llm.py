"""Shared helpers for LLM nodes: prompt files, JSON extraction, token accounting."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from virasat.llm.router import get_chat, model_spec

log = structlog.get_logger()
PROMPTS = Path(__file__).parent / "prompts"
PROMPT_VERSIONS = {"assess": "assess.v1.md", "verify": "verify.v1.md"}
TOKENS: dict[str, int] = defaultdict(int)  # change_id -> tokens used in this process


def prompt(node: str) -> str:
    return (PROMPTS / PROMPT_VERSIONS[node]).read_text()


def extract_json(text: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    data: dict[str, Any] = json.loads(m.group(0))
    return data


def call(node: str, change_id: str, text: str, llm: BaseChatModel | None = None) -> str:
    llm = llm or get_chat(node)
    msg = llm.invoke(text)
    content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
    used = 0
    if isinstance(msg, AIMessage) and msg.usage_metadata:
        used = int(msg.usage_metadata.get("total_tokens", 0))
    TOKENS[change_id] += used
    log.info(
        "llm_call",
        change_id=change_id,
        node=node,
        model=model_spec(node)["model"],
        prompt_version=PROMPT_VERSIONS[node],
        tokens=used,
    )
    log.debug("llm_raw", change_id=change_id, node=node, output=content)
    return content
