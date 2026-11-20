"""Foundation Models recovery bridge status + operator query API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from streamtv.config import config
from streamtv.utils.ai_backend_selector import macos_major_version, resolve_backend
from streamtv.utils.foundation_models_client import FoundationModelsClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["FoundationModels"])

BASE_DIR = Path(__file__).parent.parent
_TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _template_missing_response(name: str) -> HTMLResponse:
    body = (
        "<!DOCTYPE html><html><head><title>StreamTV — template missing</title></head>"
        "<body><h1>503 — template not installed</h1>"
        f"<p>Missing <code>streamtv/templates/{name}</code>. "
        "Reinstall StreamTV or sync the repo templates directory.</p></body></html>"
    )
    return HTMLResponse(content=body, status_code=503)


class QueryBody(BaseModel):
    query: str = Field(..., min_length=1)
    include_streamtv_logs: bool = False
    max_log_lines: int = 40


class RecoverBody(BaseModel):
    prompt: str = "Run recovery health check"
    apply_fixes: bool = False


class UnifiedQueryBody(BaseModel):
    query: str = Field(..., min_length=1)
    backend: Literal["auto", "foundation_models", "ollama"] = "auto"
    include_streamtv_logs: bool = False
    include_plex_logs: bool = False
    max_log_lines: int = 40
    model: Optional[str] = None


def _fm_url() -> str:
    return getattr(config.auto_healer, "foundation_models_url", "http://127.0.0.1:11435")


@router.get("/foundation-models")
async def foundation_models_page(request: Request):
    """Serve FM page when template exists; else redirect to /ollama; never 500."""
    fm_tpl = _TEMPLATES_DIR / "foundation_models.html"
    ollama_tpl = _TEMPLATES_DIR / "ollama.html"
    if fm_tpl.is_file():
        try:
            return templates.TemplateResponse(
                request,
                "foundation_models.html",
                {
                    "fm_url": _fm_url(),
                    "ai_backend": getattr(config.auto_healer, "ai_backend", "auto"),
                    "macos_major": macos_major_version(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — never unhandled 500 for missing Jinja
            logger.warning("foundation_models template render failed: %s", exc)
            return _template_missing_response("foundation_models.html")
    if ollama_tpl.is_file():
        # Canonical AI Recovery UI when dedicated FM template is absent.
        return RedirectResponse(url="/ollama", status_code=302)
    return _template_missing_response("foundation_models.html")


@router.get("/foundation-models/status")
async def foundation_models_status():
    client = FoundationModelsClient(base_url=_fm_url())
    try:
        status = await client.status()
        status["configured_backend"] = getattr(config.auto_healer, "ai_backend", "auto")
        status["macos_major"] = macos_major_version()
        status["bridge_url"] = _fm_url()
        return JSONResponse(status)
    finally:
        await client.client.aclose()


@router.post("/foundation-models/query")
async def foundation_models_query(body: QueryBody):
    client = FoundationModelsClient(base_url=_fm_url())
    try:
        if not await client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Foundation Models bridge unavailable. Start StreamTVMac with AI backend = Foundation Models (macOS 26+).",
            )
        prompt = body.query
        if body.include_streamtv_logs:
            prompt += f"\n(Include up to {body.max_log_lines} log lines in analysis if useful.)"
        result = await client.query(prompt)
        return JSONResponse(result)
    finally:
        await client.client.aclose()


@router.post("/foundation-models/recover")
async def foundation_models_recover(body: RecoverBody):
    client = FoundationModelsClient(base_url=_fm_url())
    try:
        if not await client.is_available():
            raise HTTPException(status_code=503, detail="FM bridge unavailable")
        apply = body.apply_fixes and bool(config.auto_healer.apply_fixes)
        result = await client.recover(prompt=body.prompt, apply_fixes=apply)
        return JSONResponse(result)
    finally:
        await client.client.aclose()


async def _probe_backends() -> tuple[bool, bool, Dict[str, Any], Dict[str, Any]]:
    fm_info: Dict[str, Any] = {}
    ollama_info: Dict[str, Any] = {
        "url": config.auto_healer.ollama_url,
        "model": config.auto_healer.ollama_model,
    }
    fm_ok = False
    ollama_ok = False

    fm = FoundationModelsClient(base_url=_fm_url())
    try:
        fm_info = await fm.status()
        fm_ok = await fm.is_available()
        fm_info["available"] = fm_ok
    except Exception as exc:
        fm_info = {"available": False, "error": str(exc)}
        fm_ok = False
    finally:
        await fm.client.aclose()

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{config.auto_healer.ollama_url.rstrip('/')}/api/tags")
            ollama_ok = r.status_code == 200
            ollama_info["available"] = ollama_ok
    except Exception as exc:
        ollama_info["available"] = False
        ollama_info["error"] = str(exc)
        ollama_ok = False

    return fm_ok, ollama_ok, fm_info, ollama_info


@router.get("/api/ai/status")
async def unified_ai_status() -> Dict[str, Any]:
    """Unified status for FM bridge + Ollama (operator dashboard)."""
    fm_ok, ollama_ok, fm_info, ollama_info = await _probe_backends()
    configured = getattr(config.auto_healer, "ai_backend", "auto")
    resolved = resolve_backend(
        configured, fm_available=fm_ok, ollama_available=ollama_ok
    )
    return {
        "ai_backend_config": configured,
        "resolved_backend": resolved,
        "macos_major": macos_major_version(),
        "foundation_models": fm_info,
        "foundation_models_url": _fm_url(),
        "ollama": ollama_info,
    }


@router.post("/api/ai/query")
async def unified_ai_query(body: UnifiedQueryBody) -> Dict[str, Any]:
    """Route operator Ask to FM bridge or Ollama based on availability / preference."""
    fm_ok, ollama_ok, _, _ = await _probe_backends()
    configured = body.backend
    if configured == "auto":
        configured = getattr(config.auto_healer, "ai_backend", "auto")
    chosen = resolve_backend(
        configured, fm_available=fm_ok, ollama_available=ollama_ok
    )

    if chosen == "none":
        raise HTTPException(
            status_code=503,
            detail=(
                "No AI backend available. Start StreamTVMac with Foundation Models "
                "(bridge :11435) or install/start Ollama."
            ),
        )

    if chosen == "foundation_models":
        client = FoundationModelsClient(base_url=_fm_url())
        try:
            prompt = body.query
            if body.include_streamtv_logs:
                prompt += (
                    f"\n(Include up to {body.max_log_lines} StreamTV log lines "
                    "in analysis if useful.)"
                )
            result = await client.query(prompt)
            if isinstance(result, dict) and result.get("error"):
                raise HTTPException(status_code=502, detail=str(result["error"]))
            text = ""
            if isinstance(result, dict):
                text = (
                    result.get("response")
                    or result.get("answer")
                    or result.get("text")
                    or ""
                )
                if not text:
                    text = str(result)
            else:
                text = str(result)
            return {
                "success": True,
                "backend": "foundation_models",
                "model": "apple_foundation_models",
                "response": text,
                "raw": result if isinstance(result, dict) else {"value": result},
                "context_used": {
                    "streamtv_logs": body.include_streamtv_logs,
                    "plex_logs": False,
                    "log_lines_analyzed": body.max_log_lines,
                },
            }
        finally:
            await client.client.aclose()

    # Ollama path — reuse install-aware helpers from ollama API module
    from streamtv.api.ollama import (
        build_ai_system_prompt,
        check_ollama_installed,
        get_installed_ollama_models,
        get_plex_logs_context,
        get_streamtv_logs_context,
    )

    if not check_ollama_installed():
        raise HTTPException(
            status_code=400,
            detail="Ollama is not installed. Use the Ollama setup section on this page.",
        )
    installed = get_installed_ollama_models()
    if not installed:
        raise HTTPException(
            status_code=400,
            detail="No Ollama models installed. Install a model from this page first.",
        )
    model = body.model or config.auto_healer.ollama_model
    if model not in installed:
        model = installed[0]

    context_parts = [build_ai_system_prompt()]
    if body.include_streamtv_logs:
        context_parts.append(get_streamtv_logs_context(body.max_log_lines))
    if body.include_plex_logs:
        context_parts.append(get_plex_logs_context(body.max_log_lines))
    full_context = "\n\n".join(context_parts)
    prompt = f"""{full_context}

User Question: {body.query}

Please analyze and provide a detailed answer with root cause and step-by-step fixes.
"""
    ollama_url = config.auto_healer.ollama_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama API error: {response.status_code}",
                )
            result = response.json()
            return {
                "success": True,
                "backend": "ollama",
                "model": model,
                "response": result.get("response", ""),
                "context_used": {
                    "streamtv_logs": body.include_streamtv_logs,
                    "plex_logs": body.include_plex_logs,
                    "log_lines_analyzed": body.max_log_lines,
                },
            }
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=500, detail="Ollama request timed out.")
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to Ollama: {exc}. Is Ollama running?",
        )
