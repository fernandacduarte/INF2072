#!/usr/bin/env python3
# designer: When a communication artifact needs to ship as a standalone HTML
#   file a stakeholder can open in a browser, I'm the converter that takes
#   your markdown and your project's communication-style configuration and
#   produces a self-contained HTML document with every CSS rule inlined --
#   no external assets, no broken references, just one file you can email
#   or attach to a ticket.
'''
md_to_html.py — Convert a markdown file to styled standalone HTML.

Invocation: user-cli
Lifecycle: active

Reads a markdown file and an optional style configuration file
(project/communication-style.md) to produce a self-contained HTML
document with all CSS inlined.

Engines
=======
  python-markdown  Default. Uses the ``markdown`` library with
                   ``jinja2`` for templating. Supports extensions:
                   tables, fenced_code, toc, meta.
  pandoc           Shell out to ``pandoc`` with options from the style
                   file. Falls back to python-markdown if pandoc is
                   not on PATH.

Usage
-----
    python .claude/skills/scripts/md_to_html.py <input.md> [options]

    --style <path>     Path to project/communication-style.md
                       (default: product-design/communication-style.md)
    --output <path>    Output HTML path (default: input stem + .html)
    --engine <name>    Override engine: python-markdown | pandoc
                       (default: from style file or python-markdown)
    --lang <code>      HTML lang attribute
                       (default: from project config or en-US)
    --verbose          Show conversion details

Run from the repository root.
'''
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

try:
    from project_config import get as _cfg_get
except ImportError:
    _cfg_get = None


def _default_lang() -> str:
    """Return the primary locale from project config, or 'en-US'."""
    if _cfg_get is not None:
        langs = _cfg_get("I18N_LANGUAGES", "en-US")
        return langs.split(",")[0].strip()
    return "en-US"
DEFAULT_STYLE_PATH = REPO_ROOT / 'product-design' / 'communication-style.md'

# ---------------------------------------------------------------------------
# Default values when no style file is available
# ---------------------------------------------------------------------------

DEFAULT_CSS = """\
body {
  max-width: 48em;
  margin: 2em auto;
  padding: 0 1em;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #222;
}
h1, h2, h3 { margin-top: 1.4em; }
code { background: #f4f4f4; padding: 0.15em 0.3em; border-radius: 3px; }
pre  { background: #f4f4f4; padding: 1em; overflow-x: auto; border-radius: 4px; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 0.5em 0.75em; text-align: left; }
th { background: #f8f8f8; }
blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #555; }
a { color: #0366d6; }
"""

DEFAULT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
{{ css }}
  </style>
</head>
<body>
{{ header }}
{{ content }}
{{ footer }}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Style file parsing
# ---------------------------------------------------------------------------

def parse_style_file(path: Path, verbose: bool = False) -> dict:
    """Extract CSS, header, footer, and engine from the style markdown.

    Looks for specific section headers and fenced code blocks within them.
    Returns a dict with keys: css, header, footer, engine, pandoc_args.
    """
    result: dict = {
        "css": DEFAULT_CSS,
        "header": "",
        "footer": "",
        "engine": "python-markdown",
        "pandoc_args": [],
    }

    if not path.is_file():
        if verbose:
            print(f"  Style file not found: {path}")
            print("  Using default styles.")
        return result

    text = path.read_text(encoding="utf-8")
    if verbose:
        print(f"  Parsing style file: {path}")

    # Split into sections by ## or section-number headings
    sections = _split_sections(text)

    for heading, body in sections:
        heading_lower = heading.lower()

        # Visual Style section — extract CSS from fenced code block
        if "visual style" in heading_lower or "§3" in heading_lower:
            css = _extract_fenced_block(body, lang_hint="css")
            if css:
                result["css"] = css
                if verbose:
                    print(f"  Extracted CSS ({len(css)}) from {SQ}{heading}{SQ}")

        # Content Framing section — extract header/footer HTML
        if "content framing" in heading_lower or "§4" in heading_lower:
            html_blocks = _extract_all_fenced_blocks(body, lang_hint="html")
            if len(html_blocks) >= 1:
                result["header"] = html_blocks[0]
                if verbose:
                    print(f"  Extracted header HTML from {SQ}{heading}{SQ}")
            if len(html_blocks) >= 2:
                result["footer"] = html_blocks[1]
                if verbose:
                    print(f"  Extracted footer HTML from {SQ}{heading}{SQ}")

        # HTML Conversion section — extract engine choice and pandoc args
        if "html conversion" in heading_lower or "§5" in heading_lower:
            engine_match = re.search(
                r"engine\s*[:=]\s*(python-markdown|pandoc)",
                body, re.IGNORECASE,
            )
            if engine_match:
                result["engine"] = engine_match.group(1).lower()
                if verbose:
                    print(f"  Engine from style: {result['engine']}")

            pandoc_match = re.search(
                r"pandoc[_-]?args\s*[:=]\s*(.+)",
                body, re.IGNORECASE,
            )
            if pandoc_match:
                result["pandoc_args"] = pandoc_match.group(1).strip().split()
                if verbose:
                    print(f"  Pandoc args: {result['pandoc_args']}")

    return result


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown text into (heading, body) tuples by level-2+ headings."""
    pattern = re.compile(r"^(#{2,}\s+.+|§\d+\s+.+)", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        return [("(preamble)", text)]

    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((heading, text[start:end]))

    return sections


def _extract_fenced_block(text: str, lang_hint: str = "") -> str:
    """Extract the first fenced code block, optionally matching a language hint."""
    pattern = re.compile(
        r"```" + re.escape(lang_hint) + r"[^\n]*\n(.*?)```",
        re.DOTALL,
    )
    m = pattern.search(text)
    if m:
        return m.group(1).strip()

    # Fallback: any fenced block
    if lang_hint:
        fallback = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
        m = fallback.search(text)
        if m:
            return m.group(1).strip()

    return ""


def _extract_all_fenced_blocks(text: str, lang_hint: str = "") -> list[str]:
    """Extract all fenced code blocks matching the language hint."""
    pattern = re.compile(
        r"```" + re.escape(lang_hint) + r"[^\n]*\n(.*?)```",
        re.DOTALL,
    )
    blocks = [m.group(1).strip() for m in pattern.finditer(text)]

    # Fallback: any fenced blocks if none matched the hint
    if not blocks and lang_hint:
        fallback = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
        blocks = [m.group(1).strip() for m in fallback.finditer(text)]

    return blocks


# ---------------------------------------------------------------------------
# Conversion engines
# ---------------------------------------------------------------------------

def convert_python_markdown(
    md_text: str, style: dict, title: str, lang: str = "en-US",
    verbose: bool = False,
) -> str:
    """Convert markdown to HTML using the python-markdown + jinja2 engine."""
    try:
        import markdown
    except ImportError:
        print("ERROR: 'markdown' library not installed.")
        print("  Install with:  pip install markdown")
        sys.exit(1)

    try:
        import jinja2
    except ImportError:
        print("ERROR: 'jinja2' library not installed.")
        print("  Install with:  pip install jinja2")
        sys.exit(1)

    extensions = ["tables", "fenced_code", "toc", "meta"]
    if verbose:
        print(f"  Markdown extensions: {extensions}")

    html_body = markdown.markdown(md_text, extensions=extensions)

    template = jinja2.Template(DEFAULT_TEMPLATE)
    html = template.render(
        title=title,
        lang=lang,
        css=style["css"],
        header=style["header"],
        content=html_body,
        footer=style["footer"],
    )

    return html


def convert_pandoc(
    input_path: Path,
    style: dict,
    title: str,
    lang: str = "en-US",
    verbose: bool = False,
) -> str:
    """Convert markdown to HTML using pandoc."""
    pandoc_bin = shutil.which("pandoc")
    if not pandoc_bin:
        print("WARNING: pandoc not found on PATH. Falling back to python-markdown.")
        md_text = input_path.read_text(encoding="utf-8")
        return convert_python_markdown(md_text, style, title, lang=lang, verbose=verbose)

    import tempfile

    cmd = [
        pandoc_bin,
        str(input_path),
        "-f", "markdown",
        "-t", "html",
        "--standalone",
        f"--metadata=title:{title}",
        f"--variable=lang:{lang}",
    ]

    # Build inline style/header content for --include-in-header
    css_html = f"<style>\n{style['css']}\n</style>"
    header_html = style.get("header", "")

    include_parts = [css_html]
    if header_html:
        include_parts.append(header_html)

    header_file = None
    footer_file = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8",
        ) as hf:
            hf.write("\n".join(include_parts))
            header_file = hf.name

        cmd.extend(["--include-in-header", header_file])

        footer_html = style.get("footer", "")
        if footer_html:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8",
            ) as ff:
                ff.write(footer_html)
                footer_file = ff.name
            cmd.extend(["--include-after-body", footer_file])

        # Add any extra pandoc args from the style file
        cmd.extend(style.get("pandoc_args", []))

        if verbose:
            print(f"  Pandoc command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding="utf-8",
        )
        return result.stdout

    except subprocess.CalledProcessError as exc:
        print(f"ERROR: pandoc failed (exit {exc.returncode}):")
        print(exc.stderr)
        sys.exit(1)

    finally:
        if header_file:
            Path(header_file).unlink(missing_ok=True)
        if footer_file:
            Path(footer_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a markdown file to styled standalone HTML.",
    )
    parser.add_argument(
        "input", type=Path,
        help="Path to the input markdown file",
    )
    parser.add_argument(
        "--style", type=Path, default=DEFAULT_STYLE_PATH,
        help="Path to project/communication-style.md "
             "(default: product-design/communication-style.md)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output HTML path (default: input stem + .html)",
    )
    parser.add_argument(
        "--engine", choices=["python-markdown", "pandoc"], default=None,
        help="Override engine (default: from style file or python-markdown)",
    )
    parser.add_argument(
        "--lang", default=None,
        help="HTML lang attribute (default: from project config or en-US)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show conversion details",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    input_path: Path = args.input.resolve()
    if not input_path.is_file():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    output_path: Path = (
        args.output.resolve()
        if args.output
        else input_path.with_suffix(".html")
    )

    title = input_path.stem.replace("-", " ").replace("_", " ").title()

    if args.verbose:
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"Title:  {title}")

    # Parse style configuration
    style = parse_style_file(args.style, verbose=args.verbose)

    # Determine lang
    lang = args.lang or _default_lang()
    if args.verbose:
        print(f"Lang:   {lang}")

    # Determine engine
    engine = args.engine or style["engine"]
    if args.verbose:
        print(f"Engine: {engine}")

    # Convert
    if engine == "pandoc":
        html = convert_pandoc(input_path, style, title, lang=lang, verbose=args.verbose)
    else:
        md_text = input_path.read_text(encoding="utf-8")
        html = convert_python_markdown(md_text, style, title, lang=lang, verbose=args.verbose)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"OK: {output_path}")
    if args.verbose:
        size_kb = output_path.stat().st_size / 1024
        print(f"  Size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
