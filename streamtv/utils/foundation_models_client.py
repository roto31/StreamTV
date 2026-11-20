"""Client for StreamTVMac Foundation Models recovery bridge (loopback HTTP)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class FoundationModelsClient:
    """Async client matching OllamaClient surface for AutoHealer dual-backend use."""

    def __init__(self, base_url: str = "http://127.0.0.1:11435") -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=90.0)
        logger.info("Initialized FoundationModelsClient base_url=%s", self.base_url)

    async def __aenter__(self) -> "FoundationModelsClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.client.aclose()

    async def is_available(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/v1/status")
            if response.status_code != 200:
                return False
            data = response.json()
            return bool(data.get("running") or data.get("bridge") == "ok")
        except Exception as exc:
            logger.warning("Foundation Models bridge not available: %s", exc)
            return False

    async def status(self) -> Dict[str, Any]:
        try:
            response = await self.client.get(f"{self.base_url}/v1/status")
            if response.status_code == 200:
                return response.json()
            return {"error": f"status {response.status_code}"}
        except Exception as exc:
            return {"error": str(exc), "available": False}

    async def list_models(self) -> List[str]:
        status = await self.status()
        if status.get("fm_available"):
            return ["system_language_model"]
        if status.get("bridge") == "ok":
            return ["bridge_heuristic"]
        return []

    async def analyze_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        log_excerpt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/analyze",
                json={
                    "error": error_message,
                    "context": context or {},
                    "log_excerpt": log_excerpt,
                },
            )
            if response.status_code == 200:
                return response.json()
            return {
                "root_cause": "Unknown - FM analysis failed",
                "severity": "medium",
                "fix_suggestions": [],
                "confidence": 0.0,
                "error": f"HTTP {response.status_code}",
            }
        except Exception as exc:
            logger.error("FM analyze_error failed: %s", exc)
            return {
                "root_cause": "Unknown - AI analysis failed",
                "severity": "medium",
                "fix_suggestions": [],
                "confidence": 0.0,
                "error": str(exc),
            }

    async def suggest_fix(
        self,
        error_type: str,
        error_details: str,
        current_config: Optional[Dict[str, Any]] = None,
        code_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/suggest",
                json={
                    "error_type": error_type,
                    "error": error_details,
                    "current_config": current_config or {},
                    "code_context": code_context,
                },
            )
            if response.status_code == 200:
                return response.json()
            return {"suggestions": [], "error": f"HTTP {response.status_code}"}
        except Exception as exc:
            logger.error("FM suggest_fix failed: %s", exc)
            return {"suggestions": [], "error": str(exc)}

    async def analyze_log_pattern(self, log_excerpt: str) -> Dict[str, Any]:
        return await self.analyze_error(
            error_message="Log pattern analysis",
            context={"task": "log_pattern"},
            log_excerpt=log_excerpt,
        )

    async def recover(
        self, prompt: str = "Run recovery health check", apply_fixes: bool = False
    ) -> Dict[str, Any]:
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/recover",
                json={"prompt": prompt, "apply_fixes": apply_fixes},
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}

    async def query(self, prompt: str) -> Dict[str, Any]:
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/query",
                json={"query": prompt},
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as exc:
            return {"error": str(exc)}
