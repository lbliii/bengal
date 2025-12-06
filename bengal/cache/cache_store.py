    def _load_data(self) -> dict | None:
        """
        Load raw data from cache file with auto-detection.

        Tries compressed format first (.json.zst), falls back to uncompressed (.json).
        This enables seamless migration from old uncompressed caches.

        Returns:
            Parsed data dict, or None if file not found or load failed
        """
        # Try compressed first (if compression enabled)
        if self._compressed_path and self._compressed_path.exists():
            try:
                from bengal.cache.compression import ZstdError, load_compressed

                return load_compressed(self._compressed_path)
            except (ZstdError, json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load compressed cache {self._compressed_path}: {e}")
                return None

        # Fall back to uncompressed JSON (for migration from old caches)
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load cache {self.cache_path}: {e}")
                return None

        # Neither file exists (normal for first build)
        logger.debug(f"Cache file not found: {self.cache_path} (will rebuild)")
        return None
