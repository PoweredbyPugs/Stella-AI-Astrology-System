"""Embedding client for the knowledge graph (Ollama, local).

Documents are embedded once at ingest time; queries are embedded per search.
Both must use the same model, which is recorded on every node as `vec_model`.

Config (environment or .env):
  STELLA_EMBED_URL    Ollama base URL            default http://127.0.0.1:11434
  STELLA_EMBED_MODEL  Ollama embedding model     default qwen3-embedding:4b
"""

from __future__ import annotations

import os

import httpx

DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3-embedding:4b"
VECTOR_INDEX = "interpretation_vec"

# Qwen3-Embedding expects an instruction on queries only; documents go in raw.
QUERY_INSTRUCTION = (
    "Instruct: Given a question or topic about astrology, divination, or esoteric philosophy, "
    "retrieve passages from books that discuss it\nQuery: "
)


class EmbeddingUnavailable(RuntimeError):
    """The embedding service could not be reached or returned an error."""


def embed_url() -> str:
    return os.environ.get("STELLA_EMBED_URL", DEFAULT_URL).rstrip("/")


def embed_model() -> str:
    return os.environ.get("STELLA_EMBED_MODEL", DEFAULT_MODEL)


def _embed(inputs: list[str], *, url: str | None, model: str | None, timeout: float,
           keep_alive: str) -> list[list[float]]:
    try:
        resp = httpx.post(
            f"{url or embed_url()}/api/embed",
            json={"model": model or embed_model(), "input": inputs, "truncate": True,
                  "keep_alive": keep_alive},
            timeout=timeout,
        )
        resp.raise_for_status()
        vectors = resp.json()["embeddings"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise EmbeddingUnavailable(str(exc)) from exc
    if len(vectors) != len(inputs):
        raise EmbeddingUnavailable(f"expected {len(inputs)} vectors, got {len(vectors)}")
    return vectors


def embed_documents(texts: list[str], *, url: str | None = None, model: str | None = None,
                    timeout: float = 600.0) -> list[list[float]]:
    return _embed(texts, url=url, model=model, timeout=timeout, keep_alive="10m")


def embed_query(query: str, *, url: str | None = None, model: str | None = None,
                timeout: float = 20.0) -> list[float]:
    """Embed a search query. Raises EmbeddingUnavailable on any failure."""
    return _embed([QUERY_INSTRUCTION + query], url=url, model=model, timeout=timeout,
                  keep_alive="30m")[0]


def document_text(text: str, title: str | None, author: str | None, section: str | None) -> str:
    """What gets embedded for a chunk: a short source header, then the chunk itself."""
    header = title or ""
    if author and author.lower() not in {"unknown", "various"}:
        header = f"{header} by {author}" if header else author
    if section and section != title:
        header = f"{header}. {section}" if header else section
    return f"{header}\n\n{text}" if header else text
