import re
import base64
from typing import Any, Tuple, List, Callable
from pathlib import Path

from .engine import WMFConverterEngine, ConversionEngineError
from .cache import WMFCache

# Regex to match WMF and EMF data URIs anywhere in HTML or raw strings
DATA_URI_PATTERN = re.compile(r'data:image/(?:x-)?(?:wmf|emf);base64,([A-Za-z0-9+/=\s]+)', re.IGNORECASE)

class JSONProcessor:
    """Recursively processes JSON data structures to find and convert embedded Base64 WMF and EMF images to PNG."""

    def __init__(self, engine: WMFConverterEngine, cache: WMFCache, temp_dir: Path, progress_callback: Callable = None):
        self.engine = engine
        self.cache = cache
        self.temp_dir = temp_dir
        self.progress_callback = progress_callback

        # Statistics
        self.total_objects: int = 0
        self.html_strings_scanned: int = 0
        self.wmf_images_found: int = 0
        self.converted_successfully: int = 0
        self.failed_conversions: int = 0
        self.errors: List[str] = []

    def count_wmf_images(self, data: Any) -> int:
        """First pass: Count total WMF/EMF images in the JSON structure for accurate progress tracking."""
        count = 0
        if isinstance(data, dict):
            for v in data.values():
                count += self.count_wmf_images(v)
        elif isinstance(data, list):
            for item in data:
                count += self.count_wmf_images(item)
        elif isinstance(data, str):
            matches = DATA_URI_PATTERN.findall(data)
            count += len(matches)
        return count

    def _convert_single_b64(self, full_match_str: str, raw_b64_str: str) -> str:
        """Helper to convert a single WMF/EMF Base64 string to a PNG data URI string using cache & engine."""
        cleaned_b64 = "".join(raw_b64_str.split())
        
        # Check hash cache first
        cached_png = self.cache.get(cleaned_b64)
        if cached_png:
            self.converted_successfully += 1
            if self.progress_callback:
                self.progress_callback()
            return f"data:image/png;base64,{cached_png}"

        # Detect extension (.emf or .wmf) from full match prefix
        ext = ".emf" if "emf" in full_match_str.lower() else ".wmf"

        # Convert WMF/EMF to PNG
        try:
            vector_bytes = base64.b64decode(cleaned_b64)
            png_bytes = self.engine.convert_wmf_to_png(vector_bytes, self.temp_dir, extension=ext)
            png_b64 = base64.b64encode(png_bytes).decode("ascii")

            # Store in cache
            self.cache.put(cleaned_b64, png_b64)
            self.converted_successfully += 1

            if self.progress_callback:
                self.progress_callback()

            return f"data:image/png;base64,{png_b64}"

        except Exception as e:
            self.failed_conversions += 1
            err_msg = f"Failed to convert image: {str(e)}"
            self.errors.append(err_msg)
            if self.progress_callback:
                self.progress_callback()
            # Return original untouched match on failure
            return full_match_str

    def _process_string_value(self, text: str) -> str:
        """Scans string for WMF/EMF data URIs and replaces them while preserving surrounding HTML."""
        self.html_strings_scanned += 1
        matches = list(DATA_URI_PATTERN.finditer(text))
        if not matches:
            return text

        self.wmf_images_found += len(matches)

        def replacer(match: re.Match) -> str:
            full_match = match.group(0)
            b64_payload = match.group(1)
            return self._convert_single_b64(full_match, b64_payload)

        # re.sub with function replaces each data URI match seamlessly
        return DATA_URI_PATTERN.sub(replacer, text)

    def process_node(self, node: Any) -> Any:
        """Recursively traverses dicts, lists, and strings in JSON structure."""
        if isinstance(node, dict):
            self.total_objects += 1
            new_dict = {}
            for key, val in node.items():
                new_dict[key] = self.process_node(val)
            return new_dict
        elif isinstance(node, list):
            return [self.process_node(item) for item in node]
        elif isinstance(node, str):
            return self._process_string_value(node)
        else:
            return node
