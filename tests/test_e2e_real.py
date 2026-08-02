import os
import sys
import json
import base64
from pathlib import Path

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
    print("   RUNNING UNIVERSAL WMF & EMF CONVERSION E2E TEST      ")
    print("========================================================\n")

    dirs = setup_app_directories()
    logger = setup_logger(dirs["base"])

    engine = WMFConverterEngine(logger=logger)
    assert engine.is_available(), "Engine should be available!"

    vec_bytes = create_valid_sample_vector_bytes()
    vec_b64 = base64.b64encode(vec_bytes).decode("ascii")

    # 1. Test Raw Data URI Input
    cache1 = WMFCache()
    proc1 = JSONProcessor(engine=engine, cache=cache1, temp_dir=dirs["temp"])
    raw_uri_input = f"data:image/x-wmf;base64,{vec_b64}"
    out1, type1 = proc1.process_universal_input(raw_uri_input)
    assert out1.startswith("data:image/png;base64,"), "Raw Data URI conversion failed!"
    assert len(proc1.converted_png_list) == 1, "Raw Data URI live PNG list failed!"
    print("[PASS] Raw Data URI input conversion & live preview payload verified.")

    # 2. Test Direct .wmf Image File Input
    test_wmf_file = dirs["temp"] / "test_input_diagram.wmf"
    with open(test_wmf_file, "wb") as f:
        f.write(vec_bytes)

    cache2 = WMFCache()
    proc2 = JSONProcessor(engine=engine, cache=cache2, temp_dir=dirs["temp"])
    out2, type2 = proc2.process_universal_input(test_wmf_file)
    assert out2.startswith("data:image/png;base64,"), "Direct .wmf file conversion failed!"
    assert len(proc2.converted_png_list) == 1, "Direct .wmf file live PNG list failed!"
    print("[PASS] Direct .wmf file input conversion verified.")

    # 3. Test Full JSON Input (WMF & EMF)
    sample_json = [
        {
            "QuestionId": 701,
            "QuestionWMF": f'<p>WMF:</p><img class="wmf" src="data:image/x-wmf;base64,{vec_b64}">',
            "QuestionEMF": f'<p>EMF:</p><img class="emf" src="data:image/x-emf;base64,{vec_b64}">'
        }
    ]
    cache3 = WMFCache()
    proc3 = JSONProcessor(engine=engine, cache=cache3, temp_dir=dirs["temp"])
    out3, type3 = proc3.process_universal_input(sample_json)
    assert "data:image/png;base64," in out3[0]["QuestionWMF"], "JSON WMF replacement failed!"
    assert "data:image/png;base64," in out3[0]["QuestionEMF"], "JSON EMF replacement failed!"
    assert len(proc3.converted_png_list) >= 1, "JSON converted PNG list failed!"
    print("[PASS] JSON structure WMF & EMF conversion verified.")

    print("\n========================================================")
    print("   SUCCESS! ALL UNIVERSAL CONVERSION TESTS PASSED!     ")
    print("========================================================\n")

if __name__ == "__main__":
    run_e2e_test()
