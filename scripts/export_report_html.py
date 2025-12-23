#!/usr/bin/env python3
"""Export a simple static HTML report from `report.json`.

Generates a lightweight, self-contained HTML file suitable for uploading as a CI artifact.
"""
import argparse
import html
import json
from pathlib import Path


def _template_html(generated_at: str, cards_html: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Test Report</title>
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <style>
    body {{ font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; padding: 1rem; }}
    .card {{ border: 1px solid #ddd; padding: 0.75rem; margin: 0.5rem 0; border-radius: 6px; }}
    .title {{ font-weight: 700; color: #333; }}
    .meta {{ color: #666; font-size: 0.9rem }}
    pre {{ background: #f6f8fa; padding: 0.5rem; border-radius: 4px; overflow: auto }}
  </style>
</head>
<body>
<h1>Test Report</h1>
<p>Generated at: {generated_at}</p>
<div id=\"cards\">
{cards_html}
</div>
</body>
</html>"""



def render_card(c: dict) -> str:
    test = html.escape(str(c.get("test", "")))
    prompt = html.escape(str(c.get("prompt", "")))
    answer = html.escape(str(c.get("answer", "")))
    parsed = html.escape(str(c.get("parsed_tool", ""))) if c.get("parsed_tool") else ""

    return f"""<div class='card'>
  <div class='title'>{test}</div>
  <div class='meta'>Prompt:</div>
  <pre>{prompt}</pre>
  <div class='meta'>Answer:</div>
  <pre>{answer}</pre>
  {f"<div class='meta'>Parsed:</div><pre>{parsed}</pre>" if parsed else ""}
</div>"""


def export_html(report_path: str, out_path: str):
    j = json.loads(Path(report_path).read_text(encoding="utf-8"))
    cards = j.get("cards", [])
    cards_html = "\n".join(render_card(c) for c in cards)
    html_out = _template_html(html.escape(j.get("generated_at", "")), cards_html)
    Path(out_path).write_text(html_out, encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--out", default="report.html")
    args = p.parse_args()
    export_html(args.report, args.out)
