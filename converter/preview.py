import os
import re
import json
import webbrowser
from pathlib import Path
from typing import Any, List, Dict

def _extract_html_fields(node: Any, path_prefix: str = "") -> List[Dict[str, str]]:
    """Recursively extracts fields containing HTML or img tags for preview cards."""
    results = []

    if isinstance(node, dict):
        for key, val in node.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            results.extend(_extract_html_fields(val, current_path))
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            current_path = f"{path_prefix}[{idx}]"
            results.extend(_extract_html_fields(item, current_path))
    elif isinstance(node, str):
        if "<" in node and ">" in node:
            results.append({"path": path_prefix, "content": node})

    return results

def generate_html_preview(json_data: Any, output_html_path: Path) -> Path:
    """
    Generates a beautiful, standalone HTML preview document containing all rendered
    questions, options, and converted PNG Base64 images with responsive sizing.
    """
    fields = _extract_html_fields(json_data)

    if not fields:
        if isinstance(json_data, list):
            for idx, item in enumerate(json_data):
                fields.append({"path": f"Item [{idx}]", "content": f"<pre>{json.dumps(item, indent=2)}</pre>"})
        else:
            fields.append({"path": "Root Object", "content": f"<pre>{json.dumps(json_data, indent=2)}</pre>"})

    cards_html = []
    for idx, field in enumerate(fields, 1):
        path_name = field["path"]
        content = field["content"]
        
        has_png = "data:image/png;base64," in content
        badge_html = '<span class="badge badge-success">✔ PNG Image</span>' if has_png else '<span class="badge">Text</span>'

        card = f"""
        <div class="card">
            <div class="card-header">
                <span class="card-num">#{idx}</span>
                <span class="card-path">{path_name}</span>
                {badge_html}
            </div>
            <div class="card-body">
                {content}
            </div>
        </div>
        """
        cards_html.append(card)

    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Converted PNG Visual HTML Preview</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-color: #f8fafc;
            --muted-color: #94a3b8;
            --primary: #38bdf8;
            --success-bg: #064e3b;
            --success-fg: #34d399;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 24px;
            line-height: 1.6;
        }}
        .header {{
            max-width: 960px;
            margin: 0 auto 24px auto;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.5rem;
            color: var(--primary);
        }}
        .header p {{
            margin: 4px 0 0 0;
            color: var(--muted-color);
            font-size: 0.9rem;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }}
        .card-header {{
            background-color: #0f172a;
            padding: 10px 16px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.85rem;
        }}
        .card-num {{
            font-weight: bold;
            color: var(--primary);
        }}
        .card-path {{
            font-family: monospace;
            color: var(--muted-color);
            flex: 1;
        }}
        .badge {{
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 12px;
            background-color: var(--border-color);
            color: var(--muted-color);
        }}
        .badge-success {{
            background-color: var(--success-bg);
            color: var(--success-fg);
            border: 1px solid var(--success-fg);
        }}
        .card-body {{
            padding: 16px;
            font-size: 1rem;
            word-wrap: break-word;
        }}
        /* Responsive Image Styling: Prevents huge bounding boxes */
        .card-body img {{
            max-width: 480px !important;
            max-height: 400px !important;
            width: auto !important;
            height: auto !important;
            display: block;
            margin: 12px 0;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background-color: #ffffff;
            padding: 6px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        pre {{
            background-color: #090d16;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.85rem;
            color: #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🌐 Converted PNG Visual Preview</h1>
            <p>Inspect rendered HTML text & cropped PNG Base64 images directly.</p>
        </div>
        <div>
            <span class="badge badge-success">{len(fields)} Fields Rendered</span>
        </div>
    </div>
    <div class="container">
        {"".join(cards_html)}
    </div>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_document)

    return output_html_path
