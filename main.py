import os
import sys
import io
import re
import json
import time
import shutil
import datetime
import threading
import webbrowser
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any, Union

# Add package directory to python path if needed
sys.path.insert(0, str(Path(__file__).parent))

from converter.utils import setup_app_directories, setup_logger
from converter.engine import WMFConverterEngine
from converter.cache import WMFCache
from converter.json_processor import JSONProcessor
from converter.report import generate_report
from converter.preview import generate_html_preview

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Pattern to truncate huge Base64 URIs ONLY for UI widget display rendering
TRUNCATE_B64_PATTERN = re.compile(
    r'(data:image/[a-zA-Z0-9\-\+]+;base64,)'
    r'([A-Za-z0-9+/=]{100})'
    r'([A-Za-z0-9+/=]{300,})'
    r'([A-Za-z0-9+/=]{20})',
    re.IGNORECASE
)

def format_text_for_fast_display(text: str) -> str:
    """
    Truncates massive single-line Base64 payloads ONLY for Tkinter UI display widgets,
    preventing Tkinter from lagging or freezing on 10MB+ single-line Base64 strings.
    The complete, un-truncated string is stored in Python RAM for 0ms copying and saving.
    """
    if len(text) < 500 or "data:image/" not in text:
        return text

    def replacer(match: re.Match) -> str:
        prefix = match.group(1)
        head = match.group(2)
        tail = match.group(4)
        omitted = len(match.group(3))
        return f"{prefix}{head}... [TRUNCATED {omitted:,} BASE64 CHARS FOR FAST DISPLAY] ...{tail}"

    return TRUNCATE_B64_PATTERN.sub(replacer, text)

def launch_interactive_gui():
    """
    High-Performance, Zero-Hang Universal WMF & EMF Converter GUI.
    Optimized for massive Base64 strings (10MB+) with memory-buffered instant copying.
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    dirs = setup_app_directories()
    logger = setup_logger(dirs["base"])

    engine = WMFConverterEngine(logger=logger)
    cache = WMFCache()

    root = tk.Tk()
    root.title("Universal WMF & EMF to PNG Base64 Converter")
    root.geometry("1100x720")
    root.minsize(880, 520)

    root.lift()
    root.focus_force()

    style = ttk.Style()
    style.theme_use("clam")

    # Header Frame
    header_frame = ttk.Frame(root, padding=(12, 10))
    header_frame.pack(fill=tk.X)

    title_label = ttk.Label(
        header_frame,
        text="Universal WMF / EMF to PNG Base64 Converter",
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

    # Fast memory storage to avoid Tkinter widget lag
    raw_input_memory = {"text": "", "file_path": None}
    current_converted_output = {
        "text": "",
        "file_path": None,
        "html_preview_path": None,
        "png_items": []
    }
    photo_image_references = []  # Keep references to avoid garbage collection
    is_converting = {"status": False}

    status_var = tk.StringVar(value="Ready. Paste JSON, raw Base64 Data URI, HTML, or open a file.")

    # Split PanedWindow
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
    left_frame = ttk.LabelFrame(paned, text=" Universal Input (JSON / Data URI / WMF / EMF / HTML) ", padding=8)
    paned.add(left_frame, weight=1)

    input_text = create_fast_text_widget(left_frame)
    input_text.focus_set()

    input_btn_frame = ttk.Frame(left_frame, padding=(0, 6, 0, 0))
    input_btn_frame.pack(fill=tk.X)

    def on_paste_input():
        try:
            clip = root.clipboard_get()
            if clip:
                raw_input_memory["text"] = clip
                raw_input_memory["file_path"] = None
                
                # Fast visual formatting for UI widget display
                display_str = format_text_for_fast_display(clip)
                input_text.delete("1.0", tk.END)
                input_text.insert("1.0", display_str)
                
                status_var.set(f"Pasted input ({len(clip):,} characters).")
        except Exception:
            messagebox.showinfo("Clipboard Empty", "Could not read text from clipboard.")

    def on_browse_file():
        selected_path = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[
                ("Supported Files", "*.json;*.wmf;*.emf;*.html;*.txt"),
                ("Vector Images", "*.wmf;*.emf"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        if selected_path:
            p = Path(selected_path)
            suf = p.suffix.lower()
            try:
                status_var.set("Loading input...")
                root.update_idletasks()
                
                if suf in (".wmf", ".emf"):
                    raw_input_memory["text"] = str(p)
                    raw_input_memory["file_path"] = p
                    input_text.delete("1.0", tk.END)
                    input_text.insert("1.0", str(p))
                    status_var.set(f"Selected image file: {p.name}")
                else:
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read()
                    raw_input_memory["text"] = content
                    raw_input_memory["file_path"] = p
                    display_str = format_text_for_fast_display(content)
                    input_text.delete("1.0", tk.END)
                    input_text.insert("1.0", display_str)
                    status_var.set(f"Loaded file: {p.name} ({len(content):,} chars)")
            except Exception as err:
                messagebox.showerror("Error Reading File", str(err))

    def on_clear_input():
        raw_input_memory["text"] = ""
        raw_input_memory["file_path"] = None
        input_text.delete("1.0", tk.END)
        current_converted_output["text"] = ""
        current_converted_output["png_items"].clear()
        photo_image_references.clear()
        output_text.delete("1.0", tk.END)
        clear_in_app_previews()
        status_var.set("Cleared input and output.")

    ttk.Button(input_btn_frame, text="📋 Paste Clipboard", command=on_paste_input).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(input_btn_frame, text="📂 Open File...", command=on_browse_file).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(input_btn_frame, text="Clear", command=on_clear_input).pack(side=tk.LEFT)

    # ------------------ RIGHT PANEL: OUTPUT & IN-APP PREVIEW ------------------
    right_frame = ttk.LabelFrame(paned, text=" Converted PNG Output & In-App Preview ", padding=8)
    paned.add(right_frame, weight=1)

    notebook = ttk.Notebook(right_frame)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    # Tab 1: Converted Output Text
    json_tab = ttk.Frame(notebook)
    notebook.add(json_tab, text=" 📄 Converted Output ")
    output_text = create_fast_text_widget(json_tab)

    # Tab 2: In-App Visual Image Preview
    visual_tab = ttk.Frame(notebook)
    notebook.add(visual_tab, text=" 🖼️ Live In-App Image Preview ")

    preview_canvas = tk.Canvas(visual_tab, bg="#1e293b", highlightthickness=0)
    preview_vscroll = ttk.Scrollbar(visual_tab, orient=tk.VERTICAL, command=preview_canvas.yview)
    preview_scrollable_frame = ttk.Frame(preview_canvas, padding=10)

    preview_scrollable_frame.bind(
        "<Configure>",
        lambda e: preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))
    )

    preview_canvas.create_window((0, 0), window=preview_scrollable_frame, anchor="nw")
    preview_canvas.configure(yscrollcommand=preview_vscroll.set)

    preview_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
    preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def clear_in_app_previews():
        for widget in preview_scrollable_frame.winfo_children():
            widget.destroy()
        photo_image_references.clear()

        placeholder_lbl = ttk.Label(
            preview_scrollable_frame,
            text="No converted PNG images to display yet.\nConvert a WMF/EMF image, JSON, or URI to see live rendered previews right here!",
            font=("Segoe UI", 10, "italic"),
            padding=20
        )
        placeholder_lbl.pack(anchor=tk.CENTER, pady=40)

    clear_in_app_previews()

    def render_in_app_previews(png_items: List[Dict[str, Any]]):
        """Renders converted PNG images directly inside the Tkinter application!"""
        clear_in_app_previews()
        for widget in preview_scrollable_frame.winfo_children():
            widget.destroy()

        if not png_items or not HAS_PIL:
            lbl = ttk.Label(
                preview_scrollable_frame,
                text="Converted string ready. (No direct embedded PNG images found or PIL unavailable)",
                font=("Segoe UI", 10)
            )
            lbl.pack(pady=20)
            return

        header_lbl = ttk.Label(
            preview_scrollable_frame,
            text=f"✔ Converted {len(png_items)} PNG Image(s) Rendered Below:",
            font=("Segoe UI", 11, "bold"),
            foreground="#008000"
        )
        header_lbl.pack(anchor=tk.W, pady=(0, 10))

        for idx, item in enumerate(png_items, 1):
            png_bytes = item["bytes"]
            path_tag = item.get("path", f"Image #{idx}")
            png_b64 = item["b64"]

            try:
                pil_img = Image.open(io.BytesIO(png_bytes))
                orig_w, orig_h = pil_img.size
                
                display_img = pil_img.copy()
                if orig_w > 450 or orig_h > 350:
                    display_img.thumbnail((450, 350), Image.Resampling.LANCZOS)

                tk_photo = ImageTk.PhotoImage(display_img)
                photo_image_references.append(tk_photo)

                card_frame = ttk.LabelFrame(
                    preview_scrollable_frame,
                    text=f" Image #{idx} ({path_tag}) ",
                    padding=10
                )
                card_frame.pack(fill=tk.X, expand=True, pady=6)

                img_label = tk.Label(card_frame, image=tk_photo, bg="#ffffff", bd=1, relief=tk.SOLID)
                img_label.pack(anchor=tk.W, pady=(0, 6))

                size_kb = len(png_bytes) / 1024.0
                info_str = f"Dimensions: {orig_w} × {orig_h} px  |  File Size: {size_kb:.1f} KB"
                info_lbl = ttk.Label(card_frame, text=info_str, font=("Segoe UI", 9), foreground="#666666")
                info_lbl.pack(anchor=tk.W)

                def make_copy_uri_cmd(b64_str=png_b64):
                    def cmd():
                        root.clipboard_clear()
                        root.clipboard_append(f"data:image/png;base64,{b64_str}")
                        root.update()
                        status_var.set("✔ Copied single PNG Data URI to clipboard!")
                    return cmd

                copy_uri_btn = ttk.Button(card_frame, text="📋 Copy PNG Data URI", command=make_copy_uri_cmd())
                copy_uri_btn.pack(anchor=tk.W, pady=(4, 0))

            except Exception as render_err:
                err_lbl = ttk.Label(preview_scrollable_frame, text=f"Error rendering Image #{idx}: {render_err}")
                err_lbl.pack(anchor=tk.W, pady=2)

    # Output Control Buttons Bar
    output_btn_frame = ttk.Frame(right_frame, padding=(0, 4, 0, 0))
    output_btn_frame.pack(fill=tk.X)

    def on_copy_output():
        # FAST 0ms COPY: Copy FULL untruncated string directly from RAM memory
        out_str = current_converted_output["text"]
        if not out_str:
            out_str = output_text.get("1.0", tk.END).strip()

        if not out_str:
            messagebox.showinfo("Output Empty", "There is no converted output to copy yet.")
            return

        try:
            root.clipboard_clear()
            root.clipboard_append(out_str)
            root.update()
            size_kb = len(out_str.encode("utf-8")) / 1024.0
            status_var.set(f"✔ Copied full converted PNG output ({size_kb:.1f} KB) to clipboard!")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy: {e}")

    def on_open_browser_preview():
        preview_p = current_converted_output["html_preview_path"]
        if preview_p and preview_p.exists():
            webbrowser.open(preview_p.as_uri())
            status_var.set(f"Opened HTML Preview in Web Browser: {preview_p.name}")
        else:
            messagebox.showinfo("Preview Not Ready", "Please convert a JSON string or vector file first.")

    def on_save_output_as():
        out_str = current_converted_output["text"]
        if not out_str:
            messagebox.showinfo("Output Empty", "There is no converted output to save yet.")
            return
        save_path = filedialog.asksaveasfilename(
            title="Save Converted Output As",
            defaultextension=".json" if out_str.startswith("{") or out_str.startswith("[") else ".txt",
            filetypes=[("JSON Files", "*.json"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(out_str)
                status_var.set(f"Saved full output to {Path(save_path).name}")
            except Exception as err:
                messagebox.showerror("Error Saving File", str(err))

    ttk.Button(output_btn_frame, text="📋 Copy Converted Output", command=on_copy_output).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(output_btn_frame, text="🌐 Open Browser HTML Preview", command=on_open_browser_preview).pack(side=tk.LEFT, padx=(0, 4))
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

        # Fetch input from RAM memory if available, otherwise from widget
        raw_input = raw_input_memory["text"] or input_text.get("1.0", tk.END).strip()
        if not raw_input:
            root.after(0, lambda: messagebox.showwarning("Input Required", "Please paste input (JSON, raw Data URI, HTML, or file path)."))
            return

        is_converting["status"] = True
        root.after(0, lambda: [
            status_var.set("⏳ Converting vector images to PNG Base64... Please wait..."),
            convert_btn.config(state=tk.DISABLED)
        ])

        start_t = time.time()
        processor = JSONProcessor(engine=engine, cache=cache, temp_dir=dirs["temp"])

        try:
            processed_output, out_type = processor.process_universal_input(raw_input)
            
            if isinstance(processed_output, (dict, list)):
                out_str = json.dumps(processed_output, ensure_ascii=False, indent=2)
            else:
                out_str = str(processed_output)

            elapsed = time.time() - start_t

            # Store COMPLETE untruncated string in RAM memory
            current_converted_output["text"] = out_str
            current_converted_output["png_items"] = list(processor.converted_png_list)

            # Save full output file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".json" if out_type == "json" else ".txt"
            output_filename = f"converted_{timestamp}{ext}"
            out_file_path = dirs["output"] / output_filename
            with open(out_file_path, "w", encoding="utf-8") as f:
                f.write(out_str)
            current_converted_output["file_path"] = out_file_path

            # Save HTML preview
            preview_filename = f"preview_{timestamp}.html"
            preview_file_path = dirs["output"] / preview_filename
            preview_data = processed_output if isinstance(processed_output, (dict, list)) else {"Result": out_str}
            generate_html_preview(preview_data, preview_file_path)
            
            latest_preview_path = dirs["output"] / "preview_latest.html"
            generate_html_preview(preview_data, latest_preview_path)
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

            # Update UI safely on main thread
            def update_ui_success():
                # Display fast truncated version in UI text box (0ms lag!)
                display_out = format_text_for_fast_display(out_str)
                output_text.delete("1.0", tk.END)
                output_text.insert("1.0", display_out)
                
                # Render live images directly inside Tkinter app window!
                render_in_app_previews(processor.converted_png_list)
                
                if len(processor.converted_png_list) > 0:
                    notebook.select(visual_tab)  # Auto-switch to Live Image Preview tab!

                convert_btn.config(state=tk.NORMAL)
                is_converting["status"] = False

                size_mb = len(out_str.encode('utf-8')) / (1024 * 1024)
                msg = f"✔ SUCCESS: Converted {processor.converted_successfully} vector image(s) ({size_mb:.2f} MB output) in {elapsed:.2f}s!"
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
    logger.info("Starting High-Performance Universal Converter GUI...")

    try:
        launch_interactive_gui()
    except Exception as e:
        logger.error(f"Fatal error in GUI application: {e}")
        print(f"Error starting application GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
