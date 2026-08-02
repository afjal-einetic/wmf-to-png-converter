import os
from pathlib import Path
from typing import List

def generate_report(
    report_file_path: Path,
    total_objects: int,
    html_strings_scanned: int,
    wmf_images_found: int,
    converted_successfully: int,
    failed_conversions: int,
    errors: List[str],
    elapsed_seconds: float,
    output_file_path: Path,
    engine_name: str
) -> str:
    """Generates report.txt file and returns the formatted report text."""

    lines = [
        "=" * 60,
        "          WMF / EMF TO PNG CONVERSION REPORT",
        "=" * 60,
        f"Engine Used             : {engine_name}",
        f"Output JSON Location    : {output_file_path}",
        f"Total Processing Time   : {elapsed_seconds:.2f} seconds",
        "-" * 60,
        "STATISTICS:",
        f"  Total JSON Objects    : {total_objects}",
        f"  HTML Strings Scanned  : {html_strings_scanned}",
        f"  Total WMF/EMF Images  : {wmf_images_found}",
        f"  Converted Successfully: {converted_successfully}",
        f"  Failed Conversions    : {failed_conversions}",
        "=" * 60,
    ]

    if errors:
        lines.append("ERRORS & WARNINGS:")
        for idx, err in enumerate(errors, 1):
            lines.append(f"  {idx}. {err}")
        lines.append("=" * 60)
    else:
        lines.append("STATUS: All conversions completed cleanly with 0 errors.")
        lines.append("=" * 60)

    report_content = "\n".join(lines) + "\n"

    try:
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
    except Exception as e:
        print(f"Warning: Could not write report file to {report_file_path}: {e}")

    return report_content
