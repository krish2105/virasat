"""Clause embeddings from the local Ollama embedding model in config/models.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from langchain_ollama import OllamaEmbeddings

from virasat.settings import settings


@lru_cache(maxsize=1)
def _model() -> tuple[OllamaEmbeddings, int]:
    cfg = yaml.safe_load(Path("config/models.yaml").read_text())["embedding"]
    return OllamaEmbeddings(model=cfg["model"], base_url=settings.ollama_base_url), cfg[
        "dimensions"
    ]


def embed_texts(texts: list[str]) -> list[list[float]]:
    model, dim = _model()
    vectors = model.embed_documents(texts)
    if any(len(v) != dim for v in vectors):
        raise RuntimeError(f"embedding dimension mismatch; expected {dim}")
    return vectors


def embed_query(text: str) -> list[float]:
    return _model()[0].embed_query(text)
