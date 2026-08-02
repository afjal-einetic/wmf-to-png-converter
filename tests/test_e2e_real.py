import os
import sys
import json
import base64
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from converter.utils import setup_app_directories, setup_logger
from converter.engine import WMFConverterEngine
from converter.cache import WMFCache
from converter.json_processor import JSONProcessor
from converter.report import generate_report

def create_valid_sample_vector_bytes() -> bytes:
    """Returns a valid minimal placeable WMF binary header + end record."""
    header = (
        b"\xd7\xcd\xc6\x9a"  # Key
        b"\x00\x00"          # hMF
        b"\x00\x00\x00\x00"  # Left, Top (0, 0)
        b"\x64\x00\x64\x00"  # Right, Bottom (100, 100)
        b"\xa0\x05"          # Inch (1440)
        b"\x00\x00\x00\x00"  # Reserved
        b"\x8d\xef"          # Checksum
        b"\x01\x00\x09\x00\x00\x03\x0f\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00"
        b"\x03\x00\x00\x00\x00\x00"
    )
    return header

def run_e2e_test():
    print("\n========================================================")
    print("   RUNNING END-TO-END WMF & EMF CONVERSION TEST         ")
    print("========================================================\n")

    dirs = setup_app_directories()
    logger = setup_logger(dirs["base"])

    # 1. Engine Detection
    engine = WMFConverterEngine(logger=logger)
    print(f"Detected Engine: {engine.engine_type}")
    print(f"Executable Path: {engine.executable_path}")
    assert engine.is_available(), "Engine should be available!"

    # 2. Prepare real input JSON with valid WMF and EMF base64 data URIs
    vec_bytes = create_valid_sample_vector_bytes()
    vec_b64 = base64.b64encode(vec_bytes).decode("ascii")

    sample_json = [
        {
            "QuestionId": 601,
            "QuestionWMF": f'<p>WMF Diagram:</p><img class="wmf-fig" style="border:1px solid black;" data-positionid="w601" width="200" height="100" src="data:image/x-wmf;base64,{vec_b64}" alt="WMF Image">',
            "QuestionEMF": f'<p>EMF Diagram:</p><img class="emf-fig" style="margin:5px;" data-positionid="e601" width="250" height="120" src="data:image/x-emf;base64,{vec_b64}" alt="EMF Image">',
            "Options": [
                {
                    "OptionText": f'<span>EMF Option:</span><img src="data:image/emf;base64,{vec_b64}">',
                    "IsCorrect": True
                }
            ]
        }
    ]

    test_input_path = dirs["input"] / "test_wmf_emf_input.json"
    with open(test_input_path, "w", encoding="utf-8") as f:
        json.dump(sample_json, f, indent=2)
    print(f"Input JSON created at: {test_input_path}")

    # 3. Process JSON
    cache = WMFCache()
    processor = JSONProcessor(engine=engine, cache=cache, temp_dir=dirs["temp"])

    total_count = processor.count_wmf_images(sample_json)
    print(f"Total WMF/EMF images detected: {total_count}")
    assert total_count == 3, f"Expected 3 WMF/EMF images, got {total_count}"

    converted_data = processor.process_node(sample_json)

    # 4. Verify Output JSON
    output_file_path = dirs["output"] / "test_wmf_emf_input.json"
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    print(f"Output JSON saved to: {output_file_path}")

    wmf_q_text = converted_data[0]["QuestionWMF"]
    emf_q_text = converted_data[0]["QuestionEMF"]

    # Verification assertions
    assert "data:image/png;base64," in wmf_q_text, "WMF PNG Data URI not found!"
    assert "data:image/x-wmf;base64," not in wmf_q_text, "Old WMF Data URI still present!"
    assert 'class="wmf-fig"' in wmf_q_text, "WMF HTML attribute class lost!"

    assert "data:image/png;base64," in emf_q_text, "EMF PNG Data URI not found!"
    assert "data:image/x-emf;base64," not in emf_q_text, "Old EMF Data URI still present!"
    assert 'class="emf-fig"' in emf_q_text, "EMF HTML attribute class lost!"

    # Verify PNG Header signature from EMF replacement
    png_b64_start = emf_q_text.find("data:image/png;base64,") + len("data:image/png;base64,")
    png_b64_end = emf_q_text.find('"', png_b64_start)
    png_b64_str = emf_q_text[png_b64_start:png_b64_end]

    decoded_png_bytes = base64.b64decode(png_b64_str)
    assert decoded_png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "EMF converted bytes do NOT match PNG header signature!"
    print("EMF to PNG Header Verification: VALID (\\x89PNG\\r\\n\\x1a\\n)")

    print("\n========================================================")
    print("   SUCCESS! BOTH WMF & EMF CONVERSION PASSED!           ")
    print("========================================================\n")

if __name__ == "__main__":
    run_e2e_test()
