import os
import sys
import json
import time
import shutil
import datetime
import threading
import webbrowser
from pathlib import Path
from typing import Tuple, Optional

# Add package directory to python path if needed
sys.path.insert(0, str(Path(__file__).parent))

from converter.utils import setup_app_directories, setup_logger
from converter.engine import WMFConverterEngine
from converter.cache import WMFCache
from converter.json_processor import JSONProcessor
from converter.report import generate_report
from converter.preview import generate_html_preview, _extract_html_fields

def launch_interactive_gui():
    """
    High-performance side-by-side interactive Tkinter GUI featuring:
    - Input JSON Text Area
    - Converted PNG JSON Output Text Area
    - Instant Copy Output button
    - Automatic Visual HTML Preview generation & 1-click Browser Preview
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    dirs = setup_app_directories()
    logger = setup_logger(dirs["base"])

    engine = WMFConverterEngine(logger=logger)
    cache = WMFCache()

    root = tk.Tk()
    root.title("WMF & EMF to PNG Base64 JSON Converter with Visual HTML Preview")
    root.geometry("1080x720")
    root.minsize(850, 520)

    # Bring to front
    root.lift()
    root.focus_force()

    style = ttk.Style()
    style.theme_use("clam")

    # Header Frame
    header_frame = ttk.Frame(root, padding=(12, 10))
    header_frame.pack(fill=tk.X)

    title_label = ttk.Label(
        header_frame,
        text="WMF / EMF to PNG Base64 Converter",
        font=("Segoe UI", 14, "bold")
    )
    title_label.pack(side=tk.LEFT)

    engine_info_str = f"Engine: {engine.engine_type.upper() if engine.is_available() else 'NOT FOUND'}"
    engine_label = ttk.Label(
        header_frame,
        text=engine_info_str,
        font=("Segoe UI", 9, "bold"),
        foreground="#008000" if engine.is_available() else "#cc0000"
    )
    engine_label.pack(side=tk.RIGHT)

    # State variables for fast memory access
    current_converted_output = {
        "text": "",
        "file_path": None,
        "html_preview_path": None,
        "json_data": None
    }
    is_converting = {"status": False}

    status_var = tk.StringVar(value="Ready. Paste JSON string or open a file.")

    # Main Split PanedWindow
    paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

    def create_fast_text_widget(parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)

        text_widget = tk.Text(
            frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=False,
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )

        v_scroll.config(command=text_widget.yview)
        h_scroll.config(command=text_widget.xview)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        return text_widget

    # ------------------ LEFT PANEL: INPUT ------------------
    left_frame = ttk.LabelFrame(paned, text=" Input JSON ", padding=8)
    paned.add(left_frame, weight=1)

    input_text = create_fast_text_widget(left_frame)
    input_text.focus_set()

    input_btn_frame = ttk.Frame(left_frame, padding=(0, 6, 0, 0))
    input_btn_frame.pack(fill=tk.X)

    def on_paste_input():
        try:
            clip = root.clipboard_get()
            if clip:
                input_text.delete("1.0", tk.END)
                input_text.insert("1.0", clip)
                status_var.set(f"Pasted input ({len(clip):,} characters).")
        except Exception:
            messagebox.showinfo("Clipboard Empty", "Could not read text from clipboard.")

    def on_browse_file():
        selected_path = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if selected_path:
            try:
                status_var.set("Loading file...")
                root.update_idletasks()
                with open(selected_path, "r", encoding="utf-8") as f:
                    content = f.read()
                input_text.delete("1.0", tk.END)
                input_text.insert("1.0", content)
                status_var.set(f"Loaded file: {Path(selected_path).name} ({len(content):,} chars)")
            except Exception as err:
                messagebox.showerror("Error Reading File", str(err))

    def on_clear_input():
        input_text.delete("1.0", tk.END)
        current_converted_output["text"] = ""
        current_converted_output["html_preview_path"] = None
        current_converted_output["json_data"] = None
        output_text.delete("1.0", tk.END)
        status_var.set("Cleared input and output.")

    ttk.Button(input_btn_frame, text="📋 Paste Clipboard", command=on_paste_input).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(input_btn_frame, text="📂 Open File...", command=on_browse_file).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(input_btn_frame, text="Clear", command=on_clear_input).pack(side=tk.LEFT)

    # ------------------ RIGHT PANEL: OUTPUT WITH NOTEBOOK TABS ------------------
    right_frame = ttk.LabelFrame(paned, text=" Converted PNG Output & Preview ", padding=8)
    paned.add(right_frame, weight=1)

    notebook = ttk.Notebook(right_frame)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    # Tab 1: Converted JSON Text
    json_tab = ttk.Frame(notebook)
    notebook.add(json_tab, text=" 📄 Converted JSON ")
    output_text = create_fast_text_widget(json_tab)

    # Tab 2: Visual Cards Text Overview
    visual_tab = ttk.Frame(notebook)
    notebook.add(visual_tab, text=" 🌐 Visual Preview ")
    
    preview_info_frame = ttk.Frame(visual_tab, padding=16)
    preview_info_frame.pack(fill=tk.BOTH, expand=True)

    preview_lbl = ttk.Label(
        preview_info_frame,
        text="Visual HTML Preview Ready",
        font=("Segoe UI", 12, "bold")
    )
    preview_lbl.pack(anchor=tk.W, pady=(0, 5))

    preview_desc = ttk.Label(
        preview_info_frame,
        text="Click the button below to open the standalone HTML preview page directly in your Web Browser (Edge / Chrome) to visually inspect rendered questions and PNG images.",
        font=("Segoe UI", 9),
        wraplength=420
    )
    preview_desc.pack(anchor=tk.W, pady=(0, 15))

    def on_open_browser_preview():
        preview_p = current_converted_output["html_preview_path"]
        if preview_p and preview_p.exists():
            webbrowser.open(preview_p.as_uri())
            status_var.set(f"Opened HTML Preview in Web Browser: {preview_p.name}")
        else:
            messagebox.showinfo("Preview Not Ready", "Please convert a JSON string first to generate the visual HTML preview.")

    btn_open_browser = ttk.Button(
        preview_info_frame,
        text="🌐 OPEN PREVIEW IN WEB BROWSER",
        command=on_open_browser_preview
    )
    btn_open_browser.pack(anchor=tk.W, ipady=4)

    # Output Control Buttons Bar
    output_btn_frame = ttk.Frame(right_frame, padding=(0, 4, 0, 0))
    output_btn_frame.pack(fill=tk.X)

    def on_copy_output():
        out_str = current_converted_output["text"] or output_text.get("1.0", tk.END).strip()

        if not out_str:
            messagebox.showinfo("Output Empty", "There is no converted output to copy yet.")
            return

        try:
            root.clipboard_clear()
            root.clipboard_append(out_str)
            root.update()
            size_kb = len(out_str.encode("utf-8")) / 1024.0
            status_var.set(f"✔ Copied converted JSON ({size_kb:.1f} KB) to clipboard!")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {e}")

    def on_save_output_as():
        out_str = current_converted_output["text"] or output_text.get("1.0", tk.END).strip()
        if not out_str:
            messagebox.showinfo("Output Empty", "There is no converted output to save yet.")
            return
        save_path = filedialog.asksaveasfilename(
            title="Save Converted JSON As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(out_str)
                status_var.set(f"Saved output to {Path(save_path).name}")
            except Exception as err:
                messagebox.showerror("Error Saving File", str(err))

    ttk.Button(output_btn_frame, text="📋 Copy Converted JSON", command=on_copy_output).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(output_btn_frame, text="🌐 Open HTML Preview", command=on_open_browser_preview).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(output_btn_frame, text="💾 Save As...", command=on_save_output_as).pack(side=tk.LEFT)

    # ------------------ CENTER ACTION BAR ------------------
    action_frame = ttk.Frame(root, padding=(12, 6))
    action_frame.pack(fill=tk.X)

    convert_btn = ttk.Button(action_frame, text="⚡ CONVERT WMF / EMF TO PNG")
    convert_btn.pack(side=tk.RIGHT, padx=5)

    def run_conversion_worker():
        if is_converting["status"]:
            return

        if not engine.is_available():
            root.after(0, lambda: messagebox.showerror(
                "Missing Engine",
                "Neither LibreOffice nor Inkscape is installed on this machine.\nPlease install LibreOffice to proceed."
            ))
            return

        raw_input = input_text.get("1.0", tk.END).strip()
        if not raw_input:
            root.after(0, lambda: messagebox.showwarning("Input Required", "Please paste a JSON string or load a JSON file into the left box."))
            return

        try:
            json_data = json.loads(raw_input)
        except Exception as json_err:
            root.after(0, lambda: messagebox.showerror("Invalid JSON Format", f"The input text is not valid JSON:\n\n{str(json_err)}"))
            return

        is_converting["status"] = True
        root.after(0, lambda: [
            status_var.set("⏳ Converting vector images to PNG Base64 in background... Please wait..."),
            convert_btn.config(state=tk.DISABLED)
        ])

        start_t = time.time()
        processor = JSONProcessor(engine=engine, cache=cache, temp_dir=dirs["temp"])

        try:
            converted_data = processor.process_node(json_data)
            out_str = json.dumps(converted_data, ensure_ascii=False, indent=2)
            elapsed = time.time() - start_t

            current_converted_output["text"] = out_str
            current_converted_output["json_data"] = converted_data

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"converted_{timestamp}.json"
            out_file_path = dirs["output"] / output_filename
            with open(out_file_path, "w", encoding="utf-8") as f:
                f.write(out_str)
            current_converted_output["file_path"] = out_file_path

            # Generate HTML Visual Preview file
            preview_filename = f"preview_{timestamp}.html"
            preview_file_path = dirs["output"] / preview_filename
            generate_html_preview(converted_data, preview_file_path)
            
            latest_preview_path = dirs["output"] / "preview_latest.html"
            generate_html_preview(converted_data, latest_preview_path)

            current_converted_output["html_preview_path"] = preview_file_path

            # Save report
            report_file = dirs["base"] / "report.txt"
            generate_report(
                report_file_path=report_file,
                total_objects=processor.total_objects,
                html_strings_scanned=processor.html_strings_scanned,
                wmf_images_found=processor.wmf_images_found,
                converted_successfully=processor.converted_successfully,
                failed_conversions=processor.failed_conversions,
                errors=processor.errors,
                elapsed_seconds=elapsed,
                output_file_path=out_file_path,
                engine_name=f"{engine.engine_type.upper()} ({engine.executable_path})"
            )

            # Update UI on main thread
            def update_ui_success():
                output_text.delete("1.0", tk.END)
                output_text.insert("1.0", out_str)
                convert_btn.config(state=tk.NORMAL)
                is_converting["status"] = False

                msg = f"✔ SUCCESS: Converted {processor.converted_successfully} image(s) in {elapsed:.2f}s! HTML Preview saved to output."
                status_var.set(msg)
                logger.info(msg)

            root.after(0, update_ui_success)

        except Exception as conv_err:
            def update_ui_error():
                convert_btn.config(state=tk.NORMAL)
                is_converting["status"] = False
                messagebox.showerror("Conversion Failed", f"An error occurred during conversion:\n\n{str(conv_err)}")
                status_var.set(f"Error during conversion: {conv_err}")

            root.after(0, update_ui_error)

    def on_start_conversion_click():
        if is_converting["status"]:
            return
        t = threading.Thread(target=run_conversion_worker, daemon=True)
        t.start()

    convert_btn.config(command=on_start_conversion_click)

    # Status Bar
    status_bar = ttk.Label(
        root,
        textvariable=status_var,
        relief=tk.SUNKEN,
        anchor=tk.W,
        padding=(10, 6),
        font=("Segoe UI", 9)
    )
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    root.bind("<Control-Return>", lambda ev: on_start_conversion_click())

    root.mainloop()

def main():
    dirs = setup_app_directories()
    logger = setup_logger(dirs["base"])
    logger.info("Starting High-Performance Converter GUI with Visual Preview...")

    try:
        launch_interactive_gui()
    except Exception as e:
        logger.error(f"Fatal error in GUI application: {e}")
        print(f"Error starting application GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
