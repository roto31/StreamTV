"""Archive.org downloader using the `ia` CLI tool.

Why ia CLI instead of the API?
  - The Archive.org metadata/download API is rate-limited.
  - The `ia` CLI batches requests and respects server-side throttling automatically.
  - Downloading MP4 files avoids FFmpeg transcoding overhead entirely.
  - Plex can direct-play H.264 MP4 files with no server-side CPU cost.

Prerequisites:
    pip install internetarchive
    # OR
    ia --version   # verify it is on PATH
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from ..config import config

logger = logging.getLogger(__name__)

# Format preference priority: we try each in order and take the first available.
_FORMAT_GLOBS: dict[str, list[str]] = {
    "mp4":  ["*.mp4", "*.MP4"],
    "webm": ["*.webm", "*.WEBM"],
    "h264": ["*h264*", "*H264*"],
    "best": ["*.mp4", "*.webm", "*.mkv", "*.avi", "*.mov"],
}


class ArchiveOrgDownloader:
    """Download Archive.org items to local cache using the `ia` CLI.

    This replaces direct API streaming for Archive.org content, completely
    eliminating rate-limit lockouts during development and production.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "archive_org"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ia_path = self._resolve_ia()
        self._semaphore = asyncio.Semaphore(
            config.cache.download_strategy.max_concurrent_downloads
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def download_item(
        self,
        identifier: str,
        format_preference: Optional[str] = None,
        ttl_hours: Optional[int] = None,  # noqa: ARG002 (accepted for interface parity)
    ) -> Optional[Path]:
        """Download a single Archive.org item and return the path to the file.

        Args:
            identifier: Archive.org item identifier (e.g. "BigBuckBunny").
            format_preference: "mp4", "webm", "h264", or "best".
                Defaults to config.cache.download_strategy.format_preference.
            ttl_hours: Ignored here — TTL is managed by CacheManager.

        Returns:
            Path to the downloaded file, or None on failure.
        """
        fmt = format_preference or config.cache.download_strategy.format_preference
        dest_dir = self.cache_dir / identifier

        # Return immediately if already downloaded (idempotent)
        existing = self._find_existing_file(dest_dir, fmt)
        if existing:
            logger.info(f"Already cached: {identifier} → {existing}")
            return existing

        async with self._semaphore:
            return await self._run_download(identifier, fmt, dest_dir)

    async def download_collection(
        self,
        collection_id: str,
        query: Optional[str] = None,
        format_preference: Optional[str] = None,
        max_items: int = 50,
    ) -> list[Path]:
        """Download all items in an Archive.org collection.

        Args:
            collection_id: Archive.org collection identifier.
            query: Optional additional search filter (ia search syntax).
            format_preference: Preferred format for download.
            max_items: Safety cap on number of items downloaded in one run.

        Returns:
            List of Paths for successfully downloaded files.
        """
        identifiers = await self._search_collection(
            collection_id, query, max_items
        )
        logger.info(
            f"Found {len(identifiers)} items in collection '{collection_id}'"
        )
        results: list[Path] = []
        for ident in identifiers:
            path = await self.download_item(ident, format_preference)
            if path:
                results.append(path)
        return results

    async def list_formats(self, identifier: str) -> list[str]:
        """Query available formats for an identifier via `ia` metadata.

        Returns a list of file extensions available (e.g. ['mp4', 'webm']).
        """
        if not self._ia_path:
            return ["mp4"]

        cmd = [
            self._ia_path, "metadata", identifier,
            "--target=files",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            data = json.loads(stdout.decode())
            exts = set()
            for f in data:
                name = f.get("name", "")
                suffix = Path(name).suffix.lstrip(".").lower()
                if suffix in ("mp4", "webm", "mkv", "avi", "mov", "m4v"):
                    exts.add(suffix)
            return list(exts) or ["mp4"]
        except Exception as exc:
            logger.warning(f"list_formats failed for {identifier}: {exc}")
            return ["mp4"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_download(
        self, identifier: str, fmt: str, dest_dir: Path
    ) -> Optional[Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        globs = _FORMAT_GLOBS.get(fmt, _FORMAT_GLOBS["mp4"])

        # Try each glob pattern until one succeeds
        for glob_pattern in globs:
            logger.info(
                f"Downloading {identifier} (glob={glob_pattern}) → {dest_dir}"
            )
            cmd = self._build_command(identifier, glob_pattern, dest_dir)
            if not cmd:
                return None

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=config.cache.download_timeout_seconds,
                )
                if proc.returncode == 0:
                    file = self._find_existing_file(dest_dir, fmt)
                    if file:
                        logger.info(
                            f"Downloaded {identifier}: {file.name} "
                            f"({file.stat().st_size / 1024 / 1024:.1f} MB)"
                        )
                        return file
                    logger.warning(
                        f"ia exited 0 but no file found in {dest_dir} "
                        f"for glob {glob_pattern}"
                    )
                else:
                    err = stderr.decode(errors="replace")
                    logger.warning(
                        f"ia download exited {proc.returncode} "
                        f"for {identifier}/{glob_pattern}: {err[:300]}"
                    )
            except asyncio.TimeoutError:
                logger.error(
                    f"Download timeout ({config.cache.download_timeout_seconds}s) "
                    f"for {identifier}"
                )
                # Kill the hung process
                try:
                    proc.kill()
                except Exception:
                    pass
                return None
            except Exception as exc:
                logger.error(f"Unexpected error downloading {identifier}: {exc}")
                return None

        logger.error(
            f"All format globs exhausted for {identifier} (fmt={fmt})"
        )
        return None

    def _build_command(
        self, identifier: str, glob_pattern: str, dest_dir: Path
    ) -> Optional[list[str]]:
        if not self._ia_path:
            logger.error(
                "ia CLI not found. Install with: pip install internetarchive"
            )
            return None
        cmd = [
            self._ia_path, "download",
            identifier,
            f"--glob={glob_pattern}",
            f"--destdir={self.cache_dir}",
            "--no-checksum",          # Faster; skip slow checksum verification
            "--retries=3",
        ]
        # Add authentication if configured
        if (
            config.archive_org.username
            and config.archive_org.password
        ):
            # ia reads ~/.config/internetarchive/ia.ini by default; we can
            # pass credentials inline via config if set.
            cmd += [
                f"--config-file=/dev/null",  # Prevent reading stale ia config
            ]
        return cmd

    def _find_existing_file(
        self, dest_dir: Path, fmt: str
    ) -> Optional[Path]:
        """Return the first matching file inside dest_dir for the given format."""
        if not dest_dir.exists():
            return None
        globs = _FORMAT_GLOBS.get(fmt, _FORMAT_GLOBS["best"])
        for glob_pattern in globs:
            matches = list(dest_dir.glob(glob_pattern))
            if matches:
                # Prefer largest file (best quality)
                return max(matches, key=lambda p: p.stat().st_size)
        return None

    async def _search_collection(
        self, collection_id: str, query: Optional[str], max_items: int
    ) -> list[str]:
        """Run `ia search` to get item identifiers in a collection."""
        if not self._ia_path:
            return []
        search_query = f"collection:{collection_id}"
        if query:
            search_query += f" AND ({query})"
        cmd = [
            self._ia_path, "search",
            search_query,
            "--output=json",
            f"--rows={max_items}",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )
            if proc.returncode != 0:
                logger.error(
                    f"ia search failed: {stderr.decode(errors='replace')[:300]}"
                )
                return []
            results = json.loads(stdout.decode())
            return [r["identifier"] for r in results if "identifier" in r]
        except Exception as exc:
            logger.error(f"Collection search error: {exc}")
            return []

    @staticmethod
    def _resolve_ia() -> Optional[str]:
        """Find the `ia` executable on PATH or in common venv locations."""
        path = shutil.which("ia")
        if path:
            return path
        # Try pip-installed locations inside common virtualenvs
        import sys
        for candidate in [
            str(Path(sys.executable).parent / "ia"),
            "/usr/local/bin/ia",
            "/usr/bin/ia",
            str(Path.home() / ".local/bin/ia"),
        ]:
            if Path(candidate).exists():
                return candidate
        logger.error(
            "ia CLI not found. Install with: pip install internetarchive  "
            "Then re-start StreamTV."
        )
        return None
