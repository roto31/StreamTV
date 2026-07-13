"""Archive.org cache downloader using authenticated HTTP (reuses ArchiveOrgAdapter).

Downloads restricted / rate-limited items via the same node URL + cookie auth path
used for live streaming, avoiding the ia CLI and throttled API redirect chains.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import httpx

from ..config import config

if TYPE_CHECKING:
    from ..streaming.archive_org_adapter import ArchiveOrgAdapter

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 60.0
_MAX_BACKOFF_SECONDS = 1800.0

_FORMAT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "mp4": (".mp4", ".MP4"),
    "webm": (".webm", ".WEBM"),
    "h264": ("h264", "H264"),
    "best": (".mp4", ".webm", ".mkv", ".avi", ".mov", ".m4v"),
}


class ArchiveOrgHttpDownloader:
    """Download Archive.org items to local cache over authenticated HTTP."""

    def __init__(self, cache_dir: Path, archive_org_adapter: "ArchiveOrgAdapter"):
        self.cache_dir = cache_dir / "archive_org"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._adapter = archive_org_adapter
        self._semaphore = asyncio.Semaphore(
            config.cache.download_strategy.max_concurrent_downloads
        )

    async def download_item(
        self,
        url_or_identifier: str,
        format_preference: Optional[str] = None,
    ) -> Optional[Path]:
        """Download a single item; returns final file path or None.

        Accepts either a full Archive.org download URL or a bare identifier.
        When the URL includes a filename (collection items), that file is used
        directly without requiring video_files in parent metadata.
        """
        fmt = format_preference or config.cache.download_strategy.format_preference
        filename: Optional[str] = None

        if url_or_identifier.startswith("http"):
            identifier = self._adapter.extract_identifier(url_or_identifier)
            filename = self._adapter.extract_filename(url_or_identifier)
            if not identifier:
                logger.error(
                    f"Could not parse Archive.org identifier from URL: "
                    f"{url_or_identifier[:120]}"
                )
                return None
        else:
            identifier = url_or_identifier

        dest_dir = self._dest_dir(identifier, filename)
        existing = self._find_existing_file(dest_dir, fmt, filename=filename)
        if existing:
            logger.info(f"Already cached: {identifier} → {existing}")
            return existing

        async with self._semaphore:
            return await self._download_with_retries(
                identifier, fmt, dest_dir, filename=filename
            )

    @staticmethod
    def _dest_dir(identifier: str, filename: Optional[str]) -> Path:
        """Compute cache destination directory for an identifier + optional file."""
        base = Path(identifier)
        if filename:
            safe_name = filename.replace("/", "__")
            return base / safe_name
        return base

    async def _download_with_retries(
        self,
        identifier: str,
        fmt: str,
        dest_dir: Path,
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        backoff = _INITIAL_BACKOFF_SECONDS
        last_error: Optional[str] = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = await self._download_once(
                    identifier, fmt, dest_dir, filename=filename
                )
                if result:
                    return result
                last_error = "Download returned no file"
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in (429, 500, 502, 503, 504):
                    last_error = f"HTTP {status}"
                    logger.warning(
                        f"Archive.org HTTP download rate-limited/error "
                        f"({status}) for {identifier}, attempt {attempt}/{_MAX_RETRIES}"
                    )
                else:
                    logger.error(
                        f"Archive.org HTTP download failed for {identifier}: {exc}"
                    )
                    return None
            except Exception as exc:
                last_error = str(exc)
                logger.error(
                    f"Archive.org HTTP download error for {identifier}: {exc}",
                    exc_info=True,
                )
                return None

            if attempt < _MAX_RETRIES:
                logger.info(f"Retrying {identifier} in {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)

        logger.error(
            f"Archive.org HTTP download exhausted retries for {identifier}: "
            f"{last_error}"
        )
        return None

    async def _download_once(
        self,
        identifier: str,
        fmt: str,
        dest_dir: Path,
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        if filename:
            selected_name = filename
        else:
            item_info = await self._adapter.get_item_info(identifier)
            video_files = item_info.get("video_files", [])
            if not video_files:
                logger.error(f"No video files in metadata for {identifier}")
                return None

            selected = self._select_video_file(video_files, fmt)
            if not selected:
                logger.error(f"No matching {fmt} file for {identifier}")
                return None
            selected_name = selected["name"]

        stream_url = await self._adapter.get_stream_url(identifier, selected_name)
        safe_name = selected_name.replace("/", "__")

        if filename:
            final_path = self.cache_dir / dest_dir
        else:
            item_dir = self.cache_dir / dest_dir
            item_dir.mkdir(parents=True, exist_ok=True)
            final_path = item_dir / safe_name

        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = (
            final_path.with_suffix(f"{final_path.suffix}.part")
            if final_path.suffix
            else Path(f"{final_path}.part")
        )
        if final_path.exists() and final_path.stat().st_size > 0:
            return final_path

        resume_offset = part_path.stat().st_size if part_path.exists() else 0
        headers: dict[str, str] = {}
        if resume_offset > 0:
            headers["Range"] = f"bytes={resume_offset}-"

        client = await self._adapter._ensure_authenticated()
        try:
            timeout = httpx.Timeout(
                config.cache.download_timeout_seconds,
                connect=30.0,
            )
            async with client.stream(
                "GET",
                stream_url,
                headers=headers,
                follow_redirects=True,
                timeout=timeout,
            ) as response:
                if response.status_code == 416 and resume_offset > 0:
                    part_path.unlink(missing_ok=True)
                    resume_offset = 0
                    async with client.stream(
                        "GET",
                        stream_url,
                        follow_redirects=True,
                        timeout=timeout,
                    ) as retry_response:
                        retry_response.raise_for_status()
                        await self._write_stream(retry_response, part_path, 0)
                else:
                    response.raise_for_status()
                    await self._write_stream(response, part_path, resume_offset)
        finally:
            await client.aclose()

        if not part_path.exists() or part_path.stat().st_size == 0:
            part_path.unlink(missing_ok=True)
            return None

        part_path.replace(final_path)
        logger.info(
            f"Downloaded {identifier}: {final_path.name} "
            f"({final_path.stat().st_size / 1024 / 1024:.1f} MB)"
        )
        return final_path

    @staticmethod
    async def _write_stream(
        response: httpx.Response,
        part_path: Path,
        resume_offset: int,
        max_bytes: Optional[int] = None,
    ) -> int:
        mode = "ab" if resume_offset > 0 else "wb"
        written = resume_offset
        with part_path.open(mode) as handle:
            async for chunk in response.aiter_bytes(
                chunk_size=config.streaming.chunk_size
            ):
                handle.write(chunk)
                written += len(chunk)
                if max_bytes is not None and written >= max_bytes:
                    break
        return written

    async def download_ring_buffer(
        self,
        url_or_identifier: str,
        max_bytes: int,
        format_preference: Optional[str] = None,
    ) -> Optional[Path]:
        """Download only the first ``max_bytes`` into a .part file (streaming buffer)."""
        if max_bytes <= 0:
            return None
        fmt = format_preference or config.cache.download_strategy.format_preference
        filename: Optional[str] = None

        if url_or_identifier.startswith("http"):
            identifier = self._adapter.extract_identifier(url_or_identifier)
            filename = self._adapter.extract_filename(url_or_identifier)
            if not identifier:
                return None
        else:
            identifier = url_or_identifier

        dest_dir = self._dest_dir(identifier, filename)
        async with self._semaphore:
            return await self._download_ring_buffer_once(
                identifier, fmt, dest_dir, filename=filename, max_bytes=max_bytes
            )

    async def _download_ring_buffer_once(
        self,
        identifier: str,
        fmt: str,
        dest_dir: Path,
        *,
        filename: Optional[str],
        max_bytes: int,
    ) -> Optional[Path]:
        if filename:
            selected_name = filename
        else:
            item_info = await self._adapter.get_item_info(identifier)
            video_files = item_info.get("video_files", [])
            if not video_files:
                return None
            selected = self._select_video_file(video_files, fmt)
            if not selected:
                return None
            selected_name = selected["name"]

        stream_url = await self._adapter.get_stream_url(identifier, selected_name)
        safe_name = selected_name.replace("/", "__")

        if filename:
            final_path = self.cache_dir / dest_dir
        else:
            item_dir = self.cache_dir / dest_dir
            item_dir.mkdir(parents=True, exist_ok=True)
            final_path = item_dir / safe_name

        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = (
            final_path.with_suffix(f"{final_path.suffix}.part")
            if final_path.suffix
            else Path(f"{final_path}.part")
        )

        resume_offset = part_path.stat().st_size if part_path.exists() else 0
        if resume_offset >= max_bytes:
            return part_path

        headers: dict[str, str] = {}
        if resume_offset > 0:
            headers["Range"] = f"bytes={resume_offset}-"

        client = await self._adapter._ensure_authenticated()
        try:
            timeout = httpx.Timeout(
                config.cache.download_timeout_seconds,
                connect=30.0,
            )
            async with client.stream(
                "GET",
                stream_url,
                headers=headers,
                follow_redirects=True,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                written = await self._write_stream(
                    response, part_path, resume_offset, max_bytes=max_bytes
                )
        finally:
            await client.aclose()

        if part_path.exists() and part_path.stat().st_size > 0:
            logger.info(
                f"Ring buffer: {identifier} → {part_path.name} "
                f"({part_path.stat().st_size / 1024 / 1024:.1f} MB cap {max_bytes / 1024 / 1024:.1f} MB)"
            )
            return part_path
        part_path.unlink(missing_ok=True)
        return None

    def _select_video_file(
        self, video_files: list[dict], fmt: str
    ) -> Optional[dict]:
        extensions = _FORMAT_EXTENSIONS.get(fmt, _FORMAT_EXTENSIONS["mp4"])

        def matches(file_info: dict) -> bool:
            name = file_info.get("name", "")
            lower = name.lower()
            if fmt == "h264":
                return any(token.lower() in lower for token in extensions)
            return any(lower.endswith(ext.lower()) for ext in extensions)

        preferred = [f for f in video_files if matches(f)]
        pool = preferred or video_files
        return max(pool, key=lambda f: f.get("size", 0) or 0)

    def _find_existing_file(
        self, dest_dir: Path, fmt: str, filename: Optional[str] = None
    ) -> Optional[Path]:
        scan_dir = self.cache_dir / dest_dir
        if filename:
            if scan_dir.is_file() and scan_dir.stat().st_size > 0:
                return scan_dir
            return None
        if not scan_dir.exists() or not scan_dir.is_dir():
            return None
        extensions = _FORMAT_EXTENSIONS.get(fmt, _FORMAT_EXTENSIONS["best"])
        candidates: list[Path] = []
        for child in scan_dir.iterdir():
            if child.is_file() and child.suffix != ".part":
                name = child.name
                lower = name.lower()
                if fmt == "h264":
                    if any(token.lower() in lower for token in extensions):
                        candidates.append(child)
                elif any(lower.endswith(ext.lower()) for ext in extensions):
                    candidates.append(child)
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_size)
