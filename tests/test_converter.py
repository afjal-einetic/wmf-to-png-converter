import sys
import json
import base64
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from converter.cache import WMFCache
from converter.json_processor import JSONProcessor, DATA_URI_PATTERN
from converter.report import generate_report

class MockEngine:
    """Mock engine to test converter logic without needing external LibreOffice binary."""
    def __init__(self):
        self.engine_type = "mock"
        self.executable_path = Path("mock_engine.exe")

    def is_available(self):
        return True

    def convert_wmf_to_png(self, vector_bytes: bytes, temp_dir: Path, extension: str = ".wmf") -> bytes:
        # Returns a valid 1x1 transparent PNG header + bytes
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        return png_header

def test_wmf_converter():
    print("--- Running Unit Tests for WMF to PNG Converter ---")

    # 1. Test Cache
    cache = WMFCache()
    cache.put("testb64wmf", "testb64png")
    assert cache.get("testb64wmf") == "testb64png", "Cache hit failed!"
    assert cache.get("nonexistent") is None, "Cache miss failed!"
    print("[PASS] Cache logic verified.")

    # 2. Test JSON Processor & HTML Attribute Preservation
    sample_wmf_b64 = base64.b64encode(b"dummy wmf content").decode("ascii")
    sample_json = [
        {
            "id": 1,
            "QuestionText": f'<p>Solve equation:</p><img class="math-img" style="color:red;" data-positionid="42" src="data:image/x-wmf;base64,{sample_wmf_b64}" width="100" height="50" alt="formula">',
            "Options": [
                {
                    "OptionText": f'<span>Option A</span><img src="data:image/x-wmf;base64,{sample_wmf_b64}">',
                    "IsCorrect": True
                }
            ]
        }
    ]

    temp_dir = PROJECT_ROOT / "temp"
    temp_dir.mkdir(exist_ok=True)

    mock_engine = MockEngine()
    processor = JSONProcessor(engine=mock_engine, cache=cache, temp_dir=temp_dir)

    # Count WMF images
    wmf_count = processor.count_wmf_images(sample_json)
    assert wmf_count == 2, f"Expected 2 WMF images found, got {wmf_count}"
    print(f"[PASS] WMF counting verified ({wmf_count} images found).")

    # Process JSON
    result_json = processor.process_node(sample_json)

    # Verify replacement
    q_text = result_json[0]["QuestionText"]
    assert "data:image/png;base64," in q_text, "Failed to replace data URI with data:image/png;base64,"
    assert "data:image/x-wmf;base64," not in q_text, "Old WMF data URI still present in question text!"
    assert 'class="math-img"' in q_text, "HTML attribute class was lost!"
    assert 'style="color:red;"' in q_text, "HTML attribute style was lost!"
    assert 'data-positionid="42"' in q_text, "HTML attribute data-positionid was lost!"
    assert 'width="100"' in q_text, "HTML attribute width was lost!"
    assert 'height="50"' in q_text, "HTML attribute height was lost!"
    assert 'alt="formula"' in q_text, "HTML attribute alt was lost!"

    print("[PASS] HTML attribute preservation and Base64 replacement verified.")

    # Verify Hash Cache Hits
    assert cache.hits >= 1, f"Expected cache hits >= 1, got {cache.hits}"
    print(f"[PASS] Hash caching verified ({cache.hits} hit(s)).")

    # 3. Test Report Generation
    report_file = temp_dir / "test_report.txt"
    report_text = generate_report(
        report_file_path=report_file,
        total_objects=processor.total_objects,
        html_strings_scanned=processor.html_strings_scanned,
        wmf_images_found=processor.wmf_images_found,
        converted_successfully=processor.converted_successfully,
        failed_conversions=processor.failed_conversions,
        errors=processor.errors,
        elapsed_seconds=0.12,
        output_file_path=Path("output/test.json"),
        engine_name="MockEngine"
    )
    assert report_file.exists(), "Report file was not created!"
    print("[PASS] Report generation verified.")

    print("\n>>> ALL UNIT TESTS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_wmf_converter()
