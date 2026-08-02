import os
import sys
import logging
from pathlib import Path

def get_base_dir() -> Path:
    """Returns the root directory of the application."""
    # Always resolve relative to utils.py location (root project folder)
    return Path(__file__).resolve().parent.parent

def setup_app_directories() -> dict:
    """
    Creates and returns paths for:
    - Base: project root
    - Subdirectories: input/, output/, temp/
    """
    base_dir = get_base_dir()
    
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    temp_dir = base_dir / "temp"

    for d in (base_dir, input_dir, output_dir, temp_dir):
        d.mkdir(parents=True, exist_ok=True)

    return {
        "base": base_dir,
        "input": input_dir,
        "output": output_dir,
        "temp": temp_dir
    }

def setup_logger(base_dir: Path) -> logging.Logger:
    """Configures application logger writing to converter.log and console."""
    log_file = base_dir / "converter.log"
    
    logger = logging.getLogger("WMF_To_PNG_Converter")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
