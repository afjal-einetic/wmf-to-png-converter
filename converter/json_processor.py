import os
import re
import json
import base64
from typing import Any, Tuple, List, Callable, Union, Dict
from pathlib import Path

from .engine import WMFConverterEngine, ConversionEngineError
from .cache import WMFCache

# Regex to match WMF and EMF data URIs anywhere in HTML or raw strings
DATA_URI_PATTERN = re.compile(r'data:image/(?:x-)?(?:wmf|emf);base64,([A-Za-z0-9+/=\s]+)', re.IGNORECASE)

class JSONProcessor:
    """Universal Processor that converts embedded Base64 WMF/EMF images from JSON, HTML, raw Data URIs, or files to PNG."""

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

        # Store converted PNG images for in-app GUI preview (list of dicts: {"b64": str, "bytes": bytes, "path": str})
        self.converted_png_list: List[Dict[str, Any]] = []

    def count_wmf_images(self, data: Any) -> int:
        """Counts total WMF/EMF images in any data structure, string, or URI."""
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
            # If string is a bare raw Base64 string without data:image prefix
            if count == 0 and len(data.strip()) > 30 and not "<" in data:
                try:
                    decoded = base64.b64decode(data.strip()[:64], validate=False)
                    if b"\xd7\xcd\xc6\x9a" in decoded or b"\x01\x00\x09\x00" in decoded:
                        count += 1
                except Exception:
                    pass
        return count

    def _convert_single_b64(self, full_match_str: str, raw_b64_str: str, source_path: str = "") -> str:
        """Converts a single WMF/EMF Base64 string to a PNG data URI string using cache & engine."""
        cleaned_b64 = "".join(raw_b64_str.split())
        
        # Check hash cache first
        cached_png = self.cache.get(cleaned_b64)
        if cached_png:
            self.converted_successfully += 1
            png_bytes = base64.b64decode(cached_png)
            self.converted_png_list.append({"b64": cached_png, "bytes": png_bytes, "path": source_path or "Image"})
            if self.progress_callback:
                self.progress_callback()
            return f"data:image/png;base64,{cached_png}"

        ext = ".emf" if "emf" in full_match_str.lower() else ".wmf"

        try:
            vector_bytes = base64.b64decode(cleaned_b64)
            png_bytes = self.engine.convert_wmf_to_png(vector_bytes, self.temp_dir, extension=ext)
            png_b64 = base64.b64encode(png_bytes).decode("ascii")

            self.cache.put(cleaned_b64, png_b64)
            self.converted_successfully += 1
            self.converted_png_list.append({"b64": png_b64, "bytes": png_bytes, "path": source_path or "Image"})

            if self.progress_callback:
                self.progress_callback()

            return f"data:image/png;base64,{png_b64}"

        except Exception as e:
            self.failed_conversions += 1
            err_msg = f"Failed to convert image: {str(e)}"
            self.errors.append(err_msg)
            if self.progress_callback:
                self.progress_callback()
            return full_match_str

    def _process_string_value(self, text: str, source_path: str = "") -> str:
        """Scans string for WMF/EMF data URIs or bare Base64 and replaces them."""
        self.html_strings_scanned += 1
        matches = list(DATA_URI_PATTERN.finditer(text))
        
        if matches:
            self.wmf_images_found += len(matches)

            def replacer(match: re.Match) -> str:
                full_match = match.group(0)
                b64_payload = match.group(1)
                return self._convert_single_b64(full_match, b64_payload, source_path)

            return DATA_URI_PATTERN.sub(replacer, text)

        # Check if text is a bare Data URI or bare Base64 string
        cleaned_text = text.strip()
        if cleaned_text.startswith("data:image/"):
            # Format: data:image/x-wmf;base64,AQAAAA==
            m = DATA_URI_PATTERN.search(cleaned_text)
            if m:
                self.wmf_images_found += 1
                return self._convert_single_b64(m.group(0), m.group(1), source_path)

        return text

    def process_node(self, node: Any, path_prefix: str = "") -> Any:
        """Recursively traverses dicts, lists, and strings in JSON or HTML structure."""
        if isinstance(node, dict):
            self.total_objects += 1
            new_dict = {}
            for key, val in node.items():
                curr_path = f"{path_prefix}.{key}" if path_prefix else key
                new_dict[key] = self.process_node(val, curr_path)
            return new_dict
        elif isinstance(node, list):
            new_list = []
            for idx, item in enumerate(node):
                curr_path = f"{path_prefix}[{idx}]"
                new_list.append(self.process_node(item, curr_path))
            return new_list
        elif isinstance(node, str):
            return self._process_string_value(node, path_prefix)
        else:
            return node

    def process_universal_input(self, raw_input: Union[str, Path, bytes]) -> Tuple[Any, str]:
        """
        Universal entry point: Accepts JSON strings, raw Data URIs, HTML text, direct .wmf/.emf files, or Python objects.
        Returns (processed_output_data_or_string, output_format_type).
        """
        self.converted_png_list.clear()

        # 1. Handle direct file path input
        if isinstance(raw_input, Path) or (isinstance(raw_input, str) and os.path.exists(raw_input)):
            file_path = Path(raw_input)
            suffix = file_path.suffix.lower()

            if suffix in (".wmf", ".emf"):
                with open(file_path, "rb") as f:
                    vector_bytes = f.read()
                png_bytes = self.engine.convert_wmf_to_png(vector_bytes, self.temp_dir, extension=suffix)
                png_b64 = base64.b64encode(png_bytes).decode("ascii")
                data_uri = f"data:image/png;base64,{png_b64}"
                self.converted_png_list.append({"b64": png_b64, "bytes": png_bytes, "path": file_path.name})
                self.converted_successfully += 1
                self.wmf_images_found += 1
                return data_uri, "data_uri"

            elif suffix in (".json", ".txt", ".html"):
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_input = f.read()

        # 2. String processing (JSON, HTML, or Data URI)
        if isinstance(raw_input, str):
            cleaned = raw_input.strip()

            # Try parsing as JSON first
            if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith("[") and cleaned.endswith("]")):
                try:
                    json_obj = json.loads(cleaned)
                    processed_json = self.process_node(json_obj)
                    return processed_json, "json"
                except Exception:
                    pass

            # String containing HTML or Data URI
            processed_str = self._process_string_value(cleaned)
            if processed_str.startswith("data:image/png;base64,"):
                return processed_str, "data_uri"
            else:
                return processed_str, "text"

        # 3. Fallback for object / dict / list input
        processed_data = self.process_node(raw_input)
        return processed_data, "json"
