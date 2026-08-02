import os
import sys
import io
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class ConversionEngineError(Exception):
    """Raised when WMF/EMF to PNG conversion fails or no conversion engine is found."""
    pass

def trim_and_optimize_png(png_bytes: bytes, max_dim: int = 700, margin: int = 12, threshold: int = 245) -> bytes:
    """
    Auto-crops excessive empty white margins around vector diagrams and resizes 
    oversized images to optimal dimensions for clean HTML rendering and compact Base64 storage.
    """
    if not HAS_PIL:
        return png_bytes

    try:
        image = Image.open(io.BytesIO(png_bytes))
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Create binary content mask (detect anything darker than 'threshold')
        gray = ImageOps.grayscale(image)
        bw = gray.point(lambda p: 255 if p < threshold else 0)
        bbox = bw.getbbox()

        if bbox:
            left, upper, right, lower = bbox
            w, h = image.size
            # Add padding margin
            left = max(0, left - margin)
            upper = max(0, upper - margin)
            right = min(w, right + margin)
            lower = min(h, lower + margin)
            image = image.crop((left, upper, right, lower))

        # Downscale if image is larger than max_dim (e.g. 700px)
        w, h = image.size
        if w > max_dim or h > max_dim:
            image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Save optimized PNG
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG", optimize=True)
        return output_buffer.getvalue()

    except Exception:
        # Fallback to original bytes if trimming fails
        return png_bytes

class WMFConverterEngine:
    """Handles detection of LibreOffice / Inkscape and performs WMF/EMF to PNG conversions."""

    def __init__(self, logger=None):
        self.logger = logger
        self.engine_type, self.executable_path = self._detect_engine()

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            getattr(self.logger, level, self.logger.info)(message)

    def _find_libreoffice(self) -> Optional[Path]:
        """Search system PATH and standard Windows install directories for LibreOffice (soffice)."""
        for cmd in ("soffice", "soffice.exe", "libreoffice", "libreoffice.exe"):
            found = shutil.which(cmd)
            if found:
                return Path(found)

        common_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        
        pf = Path(r"C:\Program Files")
        if pf.exists():
            for p in pf.glob("LibreOffice*/program/soffice.exe"):
                common_paths.append(str(p))

        pf86 = Path(r"C:\Program Files (x86)")
        if pf86.exists():
            for p in pf86.glob("LibreOffice*/program/soffice.exe"):
                common_paths.append(str(p))

        for path_str in common_paths:
            p = Path(path_str)
            if p.exists():
                return p

        return None

    def _find_inkscape(self) -> Optional[Path]:
        """Search system PATH and standard Windows install directories for Inkscape."""
        for cmd in ("inkscape", "inkscape.exe"):
            found = shutil.which(cmd)
            if found:
                return Path(found)

        common_paths = [
            r"C:\Program Files\Inkscape\bin\inkscape.exe",
            r"C:\Program Files\Inkscape\inkscape.exe",
            r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        ]

        for path_str in common_paths:
            p = Path(path_str)
            if p.exists():
                return p

        return None

    def _detect_engine(self) -> Tuple[Optional[str], Optional[Path]]:
        """Detect available conversion tool, prioritizing LibreOffice, then Inkscape."""
        lo_path = self._find_libreoffice()
        if lo_path:
            self._log(f"Detected LibreOffice engine: {lo_path}")
            return "libreoffice", lo_path

        ink_path = self._find_inkscape()
        if ink_path:
            self._log(f"Detected Inkscape engine: {ink_path}")
            return "inkscape", ink_path

        self._log("Neither LibreOffice nor Inkscape was detected on the system.", "warning")
        return None, None

    def is_available(self) -> bool:
        return self.engine_type is not None and self.executable_path is not None

    def convert_wmf_to_png(self, vector_bytes: bytes, temp_dir: Path, extension: str = ".wmf") -> bytes:
        """
        Converts WMF or EMF raw bytes to PNG raw bytes using the detected engine,
        then automatically crops away excess white margins and optimizes image dimensions.
        """
        if not self.is_available():
            raise ConversionEngineError(
                "No vector conversion engine (LibreOffice or Inkscape) is installed or available in system PATH."
            )

        if not extension.startswith("."):
            extension = "." + extension

        unique_id = str(uuid.uuid4())
        src_file = temp_dir / f"temp_{unique_id}{extension}"
        png_file = temp_dir / f"temp_{unique_id}.png"

        try:
            with open(src_file, "wb") as f:
                f.write(vector_bytes)

            if self.engine_type == "libreoffice":
                cmd = [
                    str(self.executable_path),
                    "--headless",
                    "--convert-to", "png",
                    "--outdir", str(temp_dir),
                    str(src_file)
                ]
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                    check=False
                )
                
                if not png_file.exists():
                    err_msg = res.stderr.decode("utf-8", errors="replace") or res.stdout.decode("utf-8", errors="replace")
                    raise ConversionEngineError(f"LibreOffice conversion failed for {extension}: {err_msg}")

            elif self.engine_type == "inkscape":
                cmd = [
                    str(self.executable_path),
                    f"--export-filename={png_file}",
                    str(src_file)
                ]
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60,
                    check=False
                )

                if not png_file.exists():
                    err_msg = res.stderr.decode("utf-8", errors="replace") or res.stdout.decode("utf-8", errors="replace")
                    raise ConversionEngineError(f"Inkscape conversion failed for {extension}: {err_msg}")

            # Read converted PNG bytes
            with open(png_file, "rb") as f:
                png_bytes = f.read()

            if not png_bytes:
                raise ConversionEngineError("Converted PNG file is 0 bytes.")

            # Post-processing: Auto-crop white borders and optimize resolution
            optimized_png = trim_and_optimize_png(png_bytes)
            return optimized_png

        finally:
            if src_file.exists():
                try:
                    src_file.unlink()
                except Exception:
                    pass
            if png_file.exists():
                try:
                    png_file.unlink()
                except Exception:
                    pass
