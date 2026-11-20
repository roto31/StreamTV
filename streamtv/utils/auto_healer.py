"""Auto-healing system coordinator - monitors, analyzes, and fixes errors automatically"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai_backend_selector import create_ai_client
from .error_fixer import ErrorFixer
from .error_monitor import ErrorMonitor

logger = logging.getLogger(__name__)


class AutoHealer:
    """Coordinates error monitoring, AI analysis, and automatic fixing."""

    def __init__(
        self,
        workspace_root: Path,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2:latest",
        foundation_models_url: str = "http://127.0.0.1:11435",
        ai_backend: str = "auto",
        dry_run: bool = True,
        enable_ai: bool = True,
        max_fix_attempts: int = 3,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.dry_run = dry_run
        self.enable_ai = enable_ai
        self.ai_backend = ai_backend
        self.foundation_models_url = foundation_models_url
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.max_fix_attempts = max(1, int(max_fix_attempts))

        self.monitor = ErrorMonitor()
        self.fixer = ErrorFixer(
            workspace_root,
            dry_run=dry_run,
            max_fix_attempts=self.max_fix_attempts,
        )
        self.ai_client: Any = None
        self.resolved_backend: str = "none"

        self.run_count = 0
        self.total_errors_detected = 0
        self.total_fixes_applied = 0
        self.last_run_time: Optional[datetime] = None

        logger.info(
            "Initialized AutoHealer (dry_run=%s, enable_ai=%s, ai_backend=%s, "
            "max_fix_attempts=%s)",
            dry_run,
            enable_ai,
            ai_backend,
            self.max_fix_attempts,
        )

    async def __aenter__(self) -> "AutoHealer":
        if self.enable_ai:
            self.ai_client, self.resolved_backend = await create_ai_client(
                ai_backend=self.ai_backend,
                foundation_models_url=self.foundation_models_url,
                ollama_url=self.ollama_url,
                ollama_model=self.ollama_model,
            )
            if self.ai_client is None:
                logger.warning("No AI backend available — continuing without AI")
                self.enable_ai = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.ai_client is not None and hasattr(self.ai_client, "__aexit__"):
            await self.ai_client.__aexit__(exc_type, exc_val, exc_tb)
        elif self.ai_client is not None and hasattr(self.ai_client, "client"):
            await self.ai_client.client.aclose()

    async def run_health_check(self) -> Dict[str, Any]:
        self.run_count += 1
        self.last_run_time = datetime.now()

        result: Dict[str, Any] = {
            "run_number": self.run_count,
            "timestamp": self.last_run_time.isoformat(),
            "dry_run": self.dry_run,
            "ai_enabled": self.enable_ai,
            "ai_backend": self.resolved_backend,
            "errors_detected": [],
            "fixes_applied": [],
            "ai_analyses": [],
            "summary": {},
        }

        try:
            logger.info("=" * 70)
            logger.info("AUTO-HEALER: Starting health check #%s", self.run_count)
            logger.info("=" * 70)

            if self.enable_ai and self.ai_client:
                available = await self.ai_client.is_available()
                result["ai_available"] = available
                result["ollama_available"] = (
                    available if self.resolved_backend == "ollama" else False
                )
                result["foundation_models_available"] = (
                    available if self.resolved_backend == "foundation_models" else False
                )
                if not available:
                    logger.warning("AI backend unavailable — continuing without AI")
                    self.enable_ai = False
                else:
                    logger.info("AI backend active: %s", self.resolved_backend)

            logger.info("Scanning recent logs for errors...")
            detected_errors, log_lines = await self.monitor.scan_recent_logs(
                minutes=60, max_lines=1000
            )

            result["errors_detected"] = detected_errors
            self.total_errors_detected += len(detected_errors)

            if not detected_errors:
                logger.info("No errors detected - system healthy!")
                result["summary"]["status"] = "healthy"
                # Still ask FM recover path for lag/stall when FM backend is active
                if self.enable_ai and self.resolved_backend == "foundation_models":
                    recover = await self._recover_with_fm()
                    if recover:
                        result["recovery"] = recover
                return result

            logger.warning("Detected %s error(s)", len(detected_errors))

            grouped_errors = self.monitor.group_errors_by_category(detected_errors)
            high_priority = self.monitor.get_high_priority_errors(detected_errors)

            result["grouped_errors"] = grouped_errors
            result["high_priority_errors"] = high_priority

            if self.enable_ai and self.ai_client:
                logger.info("Analyzing errors with AI (%s)...", self.resolved_backend)
                for error in high_priority[:5]:
                    analysis = await self._analyze_error_with_ai(error, log_lines)
                    result["ai_analyses"].append(analysis)

            logger.info("Attempting to apply fixes...")
            unique_patterns = {error["pattern_name"] for error in detected_errors}

            for pattern_name in unique_patterns:
                pattern_errors = [
                    e for e in detected_errors if e["pattern_name"] == pattern_name
                ]
                logger.info(
                    "Processing %s instance(s) of '%s'",
                    len(pattern_errors),
                    pattern_name,
                )

                ai_suggestion = None
                if self.enable_ai and pattern_errors:
                    matching_analysis = next(
                        (
                            a
                            for a in result.get("ai_analyses", [])
                            if a.get("error_pattern") == pattern_name
                        ),
                        None,
                    )
                    if matching_analysis:
                        ai_suggestion = matching_analysis.get("fix_suggestion")

                fix_result = await self.fixer.apply_fix(pattern_name, ai_suggestion)
                result["fixes_applied"].append(fix_result)

                if fix_result["success"]:
                    fixes_count = len(fix_result.get("fixes_applied", []))
                    self.total_fixes_applied += fixes_count
                    logger.info(
                        "Applied %s fix(es) for '%s'", fixes_count, pattern_name
                    )
                else:
                    logger.warning("No fix applied for '%s'", pattern_name)

            if self.enable_ai and self.resolved_backend == "foundation_models":
                recover = await self._recover_with_fm()
                if recover:
                    result["recovery"] = recover

            result["summary"] = self._generate_summary(result)

            logger.info("=" * 70)
            logger.info("AUTO-HEALER: Health check #%s complete", self.run_count)
            logger.info("  Status: %s", result["summary"]["status"])
            logger.info("  Errors detected: %s", len(detected_errors))
            logger.info("  Fixes applied: %s", result["summary"]["fixes_applied"])
            logger.info("=" * 70)

        except Exception as e:
            logger.error("Error during health check: %s", e, exc_info=True)
            result["error"] = str(e)
            result["summary"]["status"] = "error"

        return result

    async def _recover_with_fm(self) -> Optional[Dict[str, Any]]:
        client = self.ai_client
        if client is None or not hasattr(client, "recover"):
            return None
        try:
            return await client.recover(
                prompt="Check playout lag and stalled FFmpeg; prefer dry-run",
                apply_fixes=not self.dry_run,
            )
        except Exception as exc:
            logger.warning("FM recover failed: %s", exc)
            return {"error": str(exc)}

    async def _analyze_error_with_ai(
        self, error: Dict[str, Any], log_lines: List[str]
    ) -> Dict[str, Any]:
        analysis_result: Dict[str, Any] = {
            "error_pattern": error["pattern_name"],
            "error_line": error["line"],
            "ai_analysis": None,
            "fix_suggestion": None,
        }

        try:
            context = {
                "pattern": error["pattern_name"],
                "category": error["category"],
                "severity": error["severity"],
                "description": error["description"],
            }
            ai_analysis = await self.ai_client.analyze_error(
                error_message=error["line"],
                context=context,
                log_excerpt=error.get("context", ""),
            )
            analysis_result["ai_analysis"] = ai_analysis

            if ai_analysis.get("confidence", 0) > 0.6:
                fix_suggestion = await self.ai_client.suggest_fix(
                    error_type=error["category"],
                    error_details=error["line"],
                    current_config=None,
                    code_context=error.get("context", ""),
                )
                analysis_result["fix_suggestion"] = fix_suggestion

        except Exception as e:
            logger.error("Error during AI analysis: %s", e)
            analysis_result["error"] = str(e)

        return analysis_result

    def _generate_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        errors_count = len(result.get("errors_detected", []))
        fixes_applied = sum(
            len(fix.get("fixes_applied", []))
            for fix in result.get("fixes_applied", [])
            if fix.get("success")
        )
        high_priority_count = len(result.get("high_priority_errors", []))

        if errors_count == 0:
            status = "healthy"
        elif high_priority_count > 0 and fixes_applied == 0:
            status = "critical"
        elif fixes_applied > 0:
            status = "healing"
        else:
            status = "degraded"

        return {
            "status": status,
            "errors_detected": errors_count,
            "high_priority": high_priority_count,
            "fixes_applied": fixes_applied,
            "categories": list(result.get("grouped_errors", {}).keys()),
            "ai_analyses_performed": len(result.get("ai_analyses", [])),
            "ai_backend": self.resolved_backend,
            "recommendations": self._generate_recommendations(result),
        }

    def _generate_recommendations(self, result: Dict[str, Any]) -> List[str]:
        recommendations: List[str] = []
        errors_count = len(result.get("errors_detected", []))
        high_priority_count = len(result.get("high_priority_errors", []))
        fixes_applied = len(
            [f for f in result.get("fixes_applied", []) if f.get("success")]
        )

        if high_priority_count > 5:
            recommendations.append(
                f"{high_priority_count} high-priority errors detected - immediate attention recommended"
            )
        if errors_count > 0 and fixes_applied == 0:
            recommendations.append(
                "No automatic fixes available - manual intervention may be required"
            )
        if self.dry_run and fixes_applied > 0:
            recommendations.append(
                "Fixes available but not applied (dry-run mode) - run with --apply to apply fixes"
            )

        grouped = result.get("grouped_errors", {})
        if "timeout" in grouped and len(grouped["timeout"]) > 3:
            recommendations.append(
                "Multiple timeout errors - consider increasing timeout values or checking network"
            )
        if "ffmpeg" in grouped and len(grouped["ffmpeg"]) > 3:
            recommendations.append(
                "Multiple FFmpeg errors - check formats/codecs or run heal_stalled_ffmpeg dry-run"
            )
        if "connection" in grouped and len(grouped["connection"]) > 3:
            recommendations.append(
                "Multiple connection errors - check Archive.org / Plex / network"
            )
        if not recommendations:
            recommendations.append("System appears stable")
        return recommendations

    async def run_continuous_monitoring(
        self, interval_minutes: int = 30, max_iterations: Optional[int] = None
    ) -> None:
        iteration = 0
        logger.info(
            "Starting continuous monitoring (interval=%smin)", interval_minutes
        )
        try:
            while True:
                iteration += 1
                if max_iterations and iteration > max_iterations:
                    logger.info(
                        "Reached max iterations (%s), stopping", max_iterations
                    )
                    break
                await self.run_health_check()
                if max_iterations is None or iteration < max_iterations:
                    logger.info(
                        "Next health check in %s minutes...", interval_minutes
                    )
                    await asyncio.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Continuous monitoring stopped by user")
        except Exception as e:
            logger.error("Error in continuous monitoring: %s", e, exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "run_count": self.run_count,
            "total_errors_detected": self.total_errors_detected,
            "total_fixes_applied": self.total_fixes_applied,
            "last_run_time": self.last_run_time.isoformat()
            if self.last_run_time
            else None,
            "dry_run": self.dry_run,
            "ai_enabled": self.enable_ai,
            "ai_backend": self.resolved_backend,
        }
