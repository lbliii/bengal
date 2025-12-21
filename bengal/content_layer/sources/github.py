"""
GitHubSource - Content source for GitHub repositories.

Fetches markdown files from GitHub repos, supporting both public
and private repositories with token authentication.

Requires: pip install bengal[github] (installs aiohttp)
"""

from __future__ import annotations

import os
from base64 import b64decode
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

try:
    import aiohttp
except ImportError as e:
    raise ImportError(
        "GitHubSource requires aiohttp.\nInstall with: pip install bengal[github]"
    ) from e

from bengal.content_layer.entry import ContentEntry
from bengal.content_layer.source import ContentSource
from bengal.content_layer.sources.local import _parse_frontmatter
from bengal.utils.logger import get_logger

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

        from bengal.errors import BengalConfigError

        if "repo" not in config:
            raise BengalConfigError(
                f"GitHubSource '{name}' requires 'repo' in config",
                suggestion="Add 'repo' to GitHubSource configuration",
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

        Yields:
            ContentEntry for each matching file
        """
        async with aiohttp.ClientSession(headers=self._headers) as session:
            # Get tree recursively
            tree_url = f"{self.api_base}/repos/{self.repo}/git/trees/{self.branch}?recursive=1"

            async with session.get(tree_url) as resp:
                if resp.status == 404:
                    logger.error(f"Repository not found: {self.repo}")
                    return
                if resp.status == 403:
                    logger.error(f"Rate limit exceeded or access denied for {self.repo}")
                    return
                resp.raise_for_status()
                data = await resp.json()

            # Filter to matching files in path
            for item in data.get("tree", []):
                if item["type"] != "blob":
                    continue

                file_path = item["path"]

                # Filter by path prefix
                if self.path and not file_path.startswith(self.path + "/"):
                    continue

                # Filter by file extension
                if not file_path.endswith(".md"):
                    continue

                # Fetch file content
                entry = await self._fetch_file(session, file_path, item["sha"])
                if entry:
                    yield entry

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
        frontmatter, body = _parse_frontmatter(content)

        # Calculate relative path from configured path
        rel_path = path[len(self.path) :].lstrip("/") if self.path else path

        # Generate slug
        slug = rel_path.replace(".md", "").replace("\\", "/")
        if slug.endswith("/index") or slug == "index":
            slug = slug.rsplit("/index", 1)[0] or "index"

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
