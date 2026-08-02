import hashlib
from typing import Optional, Dict

class WMFCache:
    """Hash cache to avoid re-converting duplicate Base64 WMF images."""

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self.hits: int = 0
        self.misses: int = 0

    def _hash_payload(self, b64_str: str) -> str:
        """Compute SHA-256 hash of the cleaned Base64 payload string."""
        clean_str = "".join(b64_str.split())
        return hashlib.sha256(clean_str.encode("utf-8")).hexdigest()

    def get(self, b64_str: str) -> Optional[str]:
        """Returns cached PNG Base64 string if available."""
        h = self._hash_payload(b64_str)
        if h in self._cache:
            self.hits += 1
            return self._cache[h]
        self.misses += 1
        return None

    def put(self, b64_str: str, png_b64_str: str):
        """Stores converted PNG Base64 string in cache."""
        h = self._hash_payload(b64_str)
        self._cache[h] = png_b64_str
