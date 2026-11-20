"""Select AI recovery backend: Foundation Models bridge vs Ollama vs none."""

from __future__ import annotations

import logging
import platform
from typing import Any, Literal, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

AIBackendName = Literal["auto", "foundation_models", "ollama", "none"]


@runtime_checkable
class AIAnalysisClient(Protocol):
    async def is_available(self) -> bool: ...

    async def analyze_error(
        self,
        error_message: str,
        context: Optional[dict] = None,
        log_excerpt: Optional[str] = None,
    ) -> dict: ...

    async def suggest_fix(
        self,
        error_type: str,
        error_details: str,
        current_config: Optional[dict] = None,
        code_context: Optional[str] = None,
    ) -> dict: ...


def macos_major_version() -> Optional[int]:
    if platform.system() != "Darwin":
        return None
    try:
        # e.g. "26.0.0" or "15.4.1"
        release = platform.mac_ver()[0]
        if not release:
            return None
        return int(release.split(".")[0])
    except (TypeError, ValueError):
        return None


def resolve_backend(
    configured: str,
    *,
    fm_available: bool,
    ollama_available: bool,
) -> str:
    """Return concrete backend name: foundation_models | ollama | none."""
    configured = (configured or "auto").strip().lower()
    major = macos_major_version()

    if configured == "none":
        return "none"
    if configured == "foundation_models":
        return "foundation_models" if fm_available else "none"
    if configured == "ollama":
        return "ollama" if ollama_available else "none"

    # auto
    if major is not None and major >= 26 and fm_available:
        return "foundation_models"
    if ollama_available:
        return "ollama"
    if fm_available:
        return "foundation_models"
    return "none"


async def create_ai_client(
    *,
    ai_backend: str = "auto",
    foundation_models_url: str = "http://127.0.0.1:11435",
    ollama_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.2:latest",
) -> tuple[Optional[Any], str]:
    """
    Probe FM bridge and Ollama, pick backend.

    Returns (client_or_None, backend_name).
    """
    from .foundation_models_client import FoundationModelsClient
    from .ollama_client import OllamaClient

    fm = FoundationModelsClient(base_url=foundation_models_url)
    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    fm_ok = False
    ollama_ok = False
    try:
        fm_ok = await fm.is_available()
    except Exception:
        fm_ok = False
    try:
        ollama_ok = await ollama.is_available()
    except Exception:
        ollama_ok = False

    chosen = resolve_backend(
        ai_backend, fm_available=fm_ok, ollama_available=ollama_ok
    )
    logger.info(
        "AI backend resolved to %s (configured=%s fm=%s ollama=%s mac=%s)",
        chosen,
        ai_backend,
        fm_ok,
        ollama_ok,
        macos_major_version(),
    )

    if chosen == "foundation_models":
        await ollama.client.aclose()
        return fm, chosen
    if chosen == "ollama":
        await fm.client.aclose()
        return ollama, chosen

    await fm.client.aclose()
    await ollama.client.aclose()
    return None, "none"
