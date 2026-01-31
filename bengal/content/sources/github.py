"""
GitHubSource - Content source for GitHub repositories.

Fetches markdown files from GitHub repos, supporting both public
and private repositories with token authentication.

Performance Optimizations:
- Parallel file fetching with configurable concurrency (default: 10 concurrent)
- Automatic retry with exponential backoff on rate limits (429/403)
- Streaming results as they complete via asyncio.as_completed()

Requires: pip install bengal[github] (installs aiohttp)
"""

from __future__ import annotations

import asyncio
import os
from base64 import b64decode
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

try:
    import aiohttp
except ImportError as e:
    raise ImportError(
        "GitHubSource requires aiohttp. Install with: pip install bengal[github]"
    ) from e

from bengal.content.sources.entry import ContentEntry
from bengal.content.sources.source import ContentSource
from bengal.content.utils.frontmatter import parse_frontmatter
from bengal.content.utils.http_errors import raise_http_error
from bengal.content.utils.slugify import path_to_slug
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class GitHubSource(ContentSource):
    """
    Content source for GitHub repositories.

    Fetches markdown files from a GitHub repo using the GitHub API.
    Supports both public repos and private repos with token authentication.

    Configuration:
        repo: str - Repository in "owner/repo" format (required)
        branch: str - Branch name (default: "main")
        path: str - Directory path within repo (default: "")
        token: str - GitHub token (optional, uses GITHUB_TOKEN env var)
        glob: str - File pattern to match (default: "*.md")

    Performance:
        Files are fetched in parallel with a configurable concurrency limit.
        Rate limit responses (429/403) trigger automatic retry with exponential backoff.
        Results are streamed as they complete (order is non-deterministic).

    Example:
            >>> source = GitHubSource("api-docs", {
            ...     "repo": "myorg/api-docs",
            ...     "branch": "main",
            ...     "path": "docs",
            ... })
            >>> async for entry in source.fetch_all():
            ...     print(entry.title)

    """

    source_type = "github"

    # Concurrency and retry configuration
    MAX_CONCURRENT_REQUESTS = 10  # GitHub rate limit friendly
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 1.0  # seconds

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        """
        Initialize GitHub source.

        Args:
            name: Source name
            config: Configuration with 'repo' required

        Raises:
            ValueError: If 'repo' not specified
        """
        super().__init__(name, config)

        from bengal.errors import BengalConfigError, ErrorCode

        if "repo" not in config:
            raise BengalConfigError(
                f"GitHubSource '{name}' requires 'repo' in config",
                suggestion="Add 'repo' to GitHubSource configuration",
                code=ErrorCode.C002,
            )

        self.repo = config["repo"]
        self.branch = config.get("branch", "main")
        self.path = config.get("path", "").strip("/")
        self.token = config.get("token") or os.environ.get("GITHUB_TOKEN")
        self.glob_pattern = config.get("glob", "*.md")

        self.api_base = "https://api.github.com"
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Bengal-SSG/1.0",
        }
        if self.token:
            self._headers["Authorization"] = f"token {self.token}"

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """
        Fetch all markdown files from the repository.

        Files are fetched in parallel with a concurrency limit for performance.
        Results are yielded as they complete (order is non-deterministic).

        Yields:
            ContentEntry for each matching file
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            # Get tree recursively in one API call
            tree_url = f"{self.api_base}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"

            async with session.get(tree_url) as resp:
                if resp.status in (401, 403, 404):
                    raise_http_error(
                        resp.status,
                        "GitHub repository",
                        self.repo,
                        suggestion={
                            401: "Check GITHUB_TOKEN is valid and not expired",
                            403: "Check GITHUB_TOKEN is set and has read access to the repository",
                            404: f"Verify repository exists: https://github.com/{self.repo}",
                        }.get(resp.status),
                    )
                resp.raise_for_status()
                data = await resp.json()

            # Filter to matching files in path
            matching_files = [
                item
                for item in data.get("tree", [])
                if item["type"] == "blob"
                and item["path"].endswith(".md")
                and (not self.path or item["path"].startswith(self.path + "/"))
            ]

            if not matching_files:
                return

            # Fetch files in parallel with concurrency limit
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

            async def fetch_with_retry(item: dict[str, Any]) -> ContentEntry | None:
                """Fetch file with exponential backoff on rate limit."""
                async with semaphore:
                    for attempt in range(self.MAX_RETRIES):
                        try:
                            return await self._fetch_file(session, item["path"], item["sha"])
                        except aiohttp.ClientResponseError as e:
                            if e.status in (429, 403) and attempt < self.MAX_RETRIES - 1:
                                # Rate limited: exponential backoff
                                delay = self.RETRY_BACKOFF_BASE * (2**attempt)
                                logger.warning(
                                    f"Rate limited (HTTP {e.status}), "
                                    f"retrying in {delay}s: {item['path']}"
                                )
                                await asyncio.sleep(delay)
                                continue
                            raise
                    return None  # All retries exhausted

            # Create tasks for parallel fetching
            tasks = [fetch_with_retry(item) for item in matching_files]

            # Track failed files for error reporting
            failed_count = 0

            # Stream results as they complete (order not guaranteed)
            for coro in asyncio.as_completed(tasks):
                try:
                    entry = await coro
                    if entry:
                        yield entry
                except Exception as e:
                    from bengal.errors import BengalContentError, ErrorCode, record_error

                    failed_count += 1
                    fetch_error = BengalContentError(
                        f"Failed to fetch file from GitHub: {e}",
                        code=ErrorCode.N016,
                        suggestion="Check file exists and is accessible in the repository",
                        original_error=e,
                    )
                    record_error(fetch_error)
                    logger.error(f"Failed to fetch file: {e}")

            if failed_count > 0:
                logger.warning(f"Failed to fetch {failed_count}/{len(matching_files)} files")

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """
        Fetch a single file by path.

        Args:
            id: Relative path within the configured path

        Returns:
            ContentEntry if found, None otherwise
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            file_path = f"{self.path}/{id}" if self.path else id
            return await self._fetch_file(session, file_path, sha=None)

    async def _fetch_file(
        self,
        session: aiohttp.ClientSession,
        path: str,
        sha: str | None,
    ) -> ContentEntry | None:
        """
        Fetch a single file from GitHub.

        Args:
            session: aiohttp session
            path: Full path within repo
            sha: Git SHA (optional, for cache key)

        Returns:
            ContentEntry or None
        """
        url = f"{self.api_base}/repos/{self.repo}/contents/{path}?ref={self.branch}"

        async with session.get(url) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()

        # Decode content (GitHub returns base64)
        content = b64decode(data["content"]).decode("utf-8")
        frontmatter, body = parse_frontmatter(content)

        # Calculate relative path from configured path
        rel_path = path[len(self.path) :].lstrip("/") if self.path else path

        # Generate slug using shared utility
        slug = path_to_slug(rel_path)

        return ContentEntry(
            id=rel_path,
            slug=slug,
            content=body,
            frontmatter=frontmatter,
            source_type=self.source_type,
            source_name=self.name,
            source_url=f"https://github.com/{self.repo}/blob/{self.branch}/{path}",
            checksum=sha or data.get("sha"),
            last_modified=None,  # GitHub API doesn't return mtime directly
        )

    async def get_last_modified(self) -> datetime | None:
        """
        Get latest commit time for the configured path.

        Returns:
            Datetime of most recent commit or None
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/repos/{self.repo}/commits"
            params = {"sha": self.branch, "per_page": 1}
            if self.path:
                params["path"] = self.path

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            if data:
                date_str = data[0]["commit"]["committer"]["date"]
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        return None

    async def is_changed(self, cached_checksum: str | None) -> bool:
        """
        Check if repo has changed since last fetch.

        Uses latest commit SHA for the path.

        Args:
            cached_checksum: Previous commit SHA

        Returns:
            True if changed or unknown
        """
        if not cached_checksum:
            return True

        async with aiohttp.ClientSession(headers=self._headers) as session:
            url = f"{self.api_base}/repos/{self.repo}/commits"
            params = {"sha": self.branch, "per_page": 1}
            if self.path:
                params["path"] = self.path

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return True
                data = await resp.json()

            if data:
                current_sha = data[0]["sha"]
                return bool(current_sha != cached_checksum)

        return True
