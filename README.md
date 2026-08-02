# WMF & EMF to PNG Base64 JSON Converter

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

A high-performance, offline Python application for Windows that recursively scans JSON files (single object or array of objects), extracts embedded **WMF and EMF Base64 vector images** inside HTML strings, converts them to **PNG Base64**, auto-crops empty white margins, and generates standalone **Visual HTML Preview** pages.

---

## ⚡ Key Features

- 🖼️ **WMF & EMF Vector Support**: Converts `data:image/x-wmf;base64,...`, `data:image/wmf;base64,...`, `data:image/x-emf;base64,...`, and `data:image/emf;base64,...` to `data:image/png;base64,...`.
- ✂️ **Automatic White Margin Trimming**: Auto-crops empty white canvas padding around vector diagrams using PIL thresholding, reducing payload size by 70–90%.
- ⚡ **Zero-Lag Interactive GUI**: Side-by-side interface with background multi-threading and instant RAM clipboard copying.
- 🌐 **Visual HTML Preview Generator**: Automatically generates standalone `.html` preview files and provides a 1-click **Open HTML Preview** button to view rendered questions & diagrams in your web browser.
- 🔒 **HTML & JSON Integrity**: Preserves 100% of HTML attributes (`class`, `style`, `data-positionid`, `width`, `height`, `alt`), unicode, HTML entities, and JSON key ordering.
- 🔑 **SHA-256 Hash Caching**: Converts duplicate Base64 images only once and reuses the PNG output.
- 📄 **Audit Logging & Reports**: Generates detailed `report.txt` and `converter.log` audit trails.

---

## 🛠️ Prerequisites & Installation

### Step 1: Install LibreOffice (Preferred) or Inkscape
This application requires either **LibreOffice** or **Inkscape** installed on Windows to render vector WMF/EMF graphics into PNG offline.

- **LibreOffice (Recommended)**: [libreoffice.org/download](https://www.libreoffice.org/download/download/)  
  *Or via Command Prompt:*
  ```cmd
  winget install LibreOffice.LibreOffice
  ```
- **Inkscape (Alternative)**: [inkscape.org](https://inkscape.org/release/)  
  *Or via Command Prompt:*
  ```cmd
  winget install Inkscape.Inkscape
  ```

---

### Step 2: Clone Repository & Install Python Packages

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/wmf-to-png-converter.git
cd wmf-to-png-converter

# 2. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 How to Run

Launch the interactive GUI dashboard:
```bash
python main.py
```

### 💡 GUI Workflow:
1. **Paste JSON**: Paste your JSON string into the left input pane (or click **📂 Open File...** to load a `.json` file).
2. **Convert**: Click **⚡ CONVERT WMF / EMF TO PNG** (or press `Ctrl+Enter`).
3. **Copy or Preview**:
   - Click **📋 Copy Converted JSON** to copy the formatted output directly to your clipboard.
   - Click **🌐 Open HTML Preview** to view the rendered questions and cropped PNG diagrams in your default browser!

---

## 🧪 Testing

To run the automated end-to-end integration test suite:

```bash
python tests/test_e2e_real.py
```

---

## 📁 Repository Structure

```
wmf-to-png-converter/
├── main.py                  # High-performance GUI application entry point
├── pyproject.toml           # PEP 517 build & package configuration
├── requirements.txt         # Dependencies (tqdm, colorama, Pillow)
├── LICENSE                  # MIT License
├── README.md                # Documentation & GitHub guide
├── .gitignore               # Git exclusions
├── converter/               # Core converter package
│   ├── __init__.py
│   ├── cache.py             # SHA-256 base64 image cache
│   ├── engine.py            # Headless LibreOffice / Inkscape + Auto-crop engine
│   ├── json_processor.py    # Recursive JSON scanner & HTML attribute preserver
│   ├── preview.py           # Standalone HTML preview renderer
│   ├── report.py            # Summary report generator
│   └── utils.py             # Path resolver & logger configuration
├── sample_data/             # Sample JSON data for testing
│   └── sample.json
└── tests/                   # Test suite
    ├── __init__.py
    ├── test_converter.py    # Unit tests
    └── test_e2e_real.py    # End-to-end integration tests
```

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).
