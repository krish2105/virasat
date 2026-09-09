"""Model routing per node from config/models.yaml. Local (Ollama) by default; cloud only
when VIRASAT_CLOUD=1. The verifier always resolves to a different model family from
the assessor — that is the point of it."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from langchain_core.language_models import BaseChatModel

from virasat.settings import settings


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    cfg: dict[str, Any] = yaml.safe_load(Path("config/models.yaml").read_text())
    return cfg


def mode() -> str:
    return "cloud" if settings.virasat_cloud else str(_config().get("default_mode", "local"))


def model_spec(node: str) -> dict[str, Any]:
    spec: dict[str, Any] = _config()["nodes"][node][mode()]
    return spec


def get_chat(node: str) -> BaseChatModel:
    spec = model_spec(node)
    if spec["provider"] == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=spec["model"],
            temperature=spec["temperature"],
            base_url=settings.ollama_base_url,
            format="json",
        )
    if spec["provider"] == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.anthropic_api_key:
            raise RuntimeError("VIRASAT_CLOUD=1 but ANTHROPIC_API_KEY is empty")
        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=spec["model"],
            temperature=spec["temperature"],
            api_key=settings.anthropic_api_key,
            timeout=120,
            stop=None,
        )
    raise ValueError(f"unknown provider {spec['provider']}")


def assert_distinct_families() -> None:
    a, v = model_spec("assess")["model"], model_spec("verify")["model"]
    if a.split(":")[0].split("-")[0] == v.split(":")[0].split("-")[0]:
        raise RuntimeError(f"assess ({a}) and verify ({v}) share a model family")
