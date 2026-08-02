# Universal WMF & EMF to PNG Base64 Converter

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

A high-performance, general-purpose offline Python application for Windows that converts **WMF & EMF vector graphics** to **PNG Base64** from any input source (JSON, raw Base64 Data URIs, HTML text, or direct `.wmf` / `.emf` image files) and renders **Live Image Previews directly inside the application GUI**!

---

## ⚡ General-Purpose Features

- 🌐 **Universal Input Handlers**:
  1. **Raw Base64 Data URIs**: `data:image/x-wmf;base64,...` or `data:image/x-emf;base64,...`
  2. **Direct Vector Image Files**: `.wmf` and `.emf` files.
  3. **JSON Files & Strings**: Single JSON objects or arrays of objects.
  4. **HTML Content**: Strings containing `<img src="data:image/x-wmf;base64,...">` tags.
- 🖼️ **In-App Live Image Preview**: Render converted PNG images directly inside the Tkinter application (`PIL.ImageTk`) so you can inspect diagrams immediately without leaving the app!
- ✂️ **Automatic White Margin Trimming**: Auto-crops empty white canvas padding around vector diagrams using PIL thresholding, reducing payload size by 70–90%.
- ⚡ **Zero-Lag Performance**: Non-blocking background multi-threading and instant RAM clipboard copying.
- 🌐 **Browser HTML Preview (Optional)**: Automatically generates standalone `.html` preview files and provides a 1-click **Open Browser HTML Preview** button.
- 🔒 **HTML & JSON Integrity**: Preserves 100% of HTML attributes (`class`, `style`, `data-positionid`, `width`, `height`, `alt`), unicode, HTML entities, and JSON key ordering.
- 🔑 **SHA-256 Hash Caching**: Converts duplicate Base64 images only once and reuses the PNG output.

---

## 🛠️ Prerequisites & Installation

### Step 1: Install LibreOffice (Preferred) or Inkscape
- **LibreOffice (Recommended)**: [libreoffice.org/download](https://www.libreoffice.org/download/download/)  
  *Command Prompt:* `winget install LibreOffice.LibreOffice`
- **Inkscape**: [inkscape.org](https://inkscape.org/release/)  
  *Command Prompt:* `winget install Inkscape.Inkscape`

### Step 2: Clone Repository & Install Python Packages

```bash
git clone https://github.com/YOUR_USERNAME/wmf-to-png-converter.git
cd wmf-to-png-converter
pip install -r requirements.txt
```

---

## 🚀 How to Run

Launch the universal converter dashboard:
```bash
python main.py
```

### 💡 Universal Workflow:
1. **Provide Input**: Paste a raw WMF/EMF Data URI, JSON string, or click **📂 Open File...** to select a `.wmf`, `.emf`, `.json`, or `.html` file.
2. **Convert**: Click **⚡ CONVERT WMF / EMF TO PNG** (or press `Ctrl+Enter`).
3. **Inspect & Copy**:
   - The app automatically switches to the **🖼️ Live In-App Image Preview** tab, rendering converted PNG diagrams directly inside Tkinter!
   - Click **📋 Copy Converted Output** to copy converted text/JSON to your clipboard.

---

## 🧪 Testing

Run the end-to-end universal input test suite:

```bash
python tests/test_e2e_real.py
```

---

## 📁 Repository Structure

```
wmf-to-png-converter/
├── main.py                  # Universal GUI application entry point (with in-app image preview)
├── pyproject.toml           # PEP 517 build & package configuration
├── requirements.txt         # Dependencies (tqdm, colorama, Pillow)
├── LICENSE                  # MIT License
├── README.md                # Documentation & GitHub guide
├── .gitignore               # Git exclusions
├── converter/               # Core converter package
│   ├── __init__.py
│   ├── cache.py             # SHA-256 base64 image cache
│   ├── engine.py            # Headless LibreOffice / Inkscape + Auto-crop engine
│   ├── json_processor.py    # Universal input processor (Data URIs, files, JSON, HTML)
│   ├── preview.py           # Standalone HTML preview renderer
│   ├── report.py            # Summary report generator
│   └── utils.py             # Path resolver & logger configuration
├── sample_data/             # Sample JSON data for testing
│   └── sample.json
└── tests/                   # Test suite
    ├── __init__.py
    ├── test_converter.py    # Unit tests
    └── test_e2e_real.py    # End-to-end universal integration tests
```

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).
