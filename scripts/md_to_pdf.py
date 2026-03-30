#!/usr/bin/env python3
"""Convert Markdown files to PDF.

Uses the `markdown` library for MD→HTML conversion and `xhtml2pdf` for
HTML→PDF rendering.  Strips YAML frontmatter (delimited by ``---``) and
applies a clean stylesheet suitable for evaluation reports with tables.

Usage:
    python scripts/md_to_pdf.py <input.md> <output.pdf>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa


CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #1a1a1a;
}

h1 {
    font-size: 18pt;
    margin-top: 0;
    margin-bottom: 6pt;
    color: #111;
    border-bottom: 2pt solid #333;
    padding-bottom: 4pt;
}

h2 {
    font-size: 14pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
    color: #222;
    border-bottom: 1pt solid #999;
    padding-bottom: 3pt;
}

h3 {
    font-size: 12pt;
    margin-top: 14pt;
    margin-bottom: 4pt;
    color: #333;
}

h4 {
    font-size: 10pt;
    margin-top: 10pt;
    margin-bottom: 4pt;
    color: #444;
    font-style: italic;
}

p {
    margin: 4pt 0;
    text-align: justify;
}

strong {
    color: #111;
}

em {
    font-style: italic;
}

blockquote {
    margin: 8pt 0;
    padding: 6pt 12pt;
    border-left: 3pt solid #666;
    background-color: #f5f5f5;
    font-style: italic;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 8pt 0;
    font-size: 8.5pt;
}

th {
    background-color: #e8e8e8;
    font-weight: bold;
    text-align: left;
    padding: 4pt 6pt;
    border: 1pt solid #999;
}

td {
    padding: 3pt 6pt;
    border: 1pt solid #ccc;
    vertical-align: top;
}

tr:nth-child(even) td {
    background-color: #fafafa;
}

hr {
    border: none;
    border-top: 1pt solid #ccc;
    margin: 14pt 0;
}

ul, ol {
    margin: 4pt 0;
    padding-left: 20pt;
}

li {
    margin-bottom: 2pt;
}

code {
    font-family: Courier, monospace;
    font-size: 9pt;
    background-color: #f0f0f0;
    padding: 1pt 3pt;
}
"""

FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter delimited by --- lines."""
    return FRONTMATTER_RE.sub("", text, count=1)


def md_to_html(md_text: str) -> str:
    """Convert Markdown to a full HTML document with embedded CSS."""
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""


def html_to_pdf(html: str, output_path: Path) -> bool:
    """Render HTML to PDF via xhtml2pdf. Returns True on success."""
    with open(output_path, "wb") as f:
        status = pisa.CreatePDF(html, dest=f)
    return not status.err


def convert(input_path: Path, output_path: Path) -> None:
    """Full pipeline: read MD, strip frontmatter, convert to PDF."""
    md_text = input_path.read_text(encoding="utf-8")
    md_text = strip_frontmatter(md_text)
    html = md_to_html(md_text)
    ok = html_to_pdf(html, output_path)
    if ok:
        print(f"PDF written: {output_path} ({output_path.stat().st_size:,} bytes)")
    else:
        print("PDF generation failed", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.pdf>", file=sys.stderr)
        sys.exit(1)
    convert(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
