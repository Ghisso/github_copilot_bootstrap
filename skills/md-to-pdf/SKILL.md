---
name: md-to-pdf
visibility: public
description: |
  Convert Markdown files to professionally styled PDF documents with full
  support for Mermaid diagrams, LaTeX/KaTeX math equations, tables,
  syntax-highlighted code blocks, and all standard Markdown features. Use when:
  - "convert markdown to pdf", "make a pdf from this md"
  - "render this markdown", "export markdown as pdf"
  - "markdown to pdf with diagrams", "pdf from markdown with equations"
  - "generate a pdf report", "convert my notes to PDF"
  - Any request to produce print-ready documents from Markdown sources.
---

# Markdown to PDF Converter

Converts Markdown files to professionally styled PDFs with full rendering of Mermaid diagrams, LaTeX math (via KaTeX), tables, syntax-highlighted code blocks, and all standard Markdown features.

## Architecture

```text
Input .md file
     │
     ├─ Step 1: Extract ```mermaid blocks → render to SVG via mmdc (Mermaid CLI)
     │          Replace mermaid code blocks with inline <svg> in the markdown source
     │
     ├─ Step 2: pandoc converts modified markdown → standalone HTML5
     │          (--katex flag preserves raw LaTeX in <span class="math ..."> elements)
     │
     ├─ Step 3: KaTeX server-side rendering (Node.js)
     │          Replaces math spans with fully rendered KaTeX HTML (no client-side JS)
     │
     ├─ Step 4: CSS injection
     │          KaTeX stylesheet + professional document styles + optional custom CSS
     │
     └─ Step 5: Playwright (headless Chromium) prints final HTML → PDF
                 ↓
           Output .pdf file
```

## Supported Features

| Feature | Rendering Engine | Notes |
|---|---|---|
| Mermaid diagrams | mmdc (mermaid-cli) via Puppeteer | flowchart, sequence, class, state, ER, gantt, pie, git, mindmap |
| LaTeX math (inline) | KaTeX server-side | `$E=mc^2$` syntax |
| LaTeX math (display) | KaTeX server-side | `$$\int f(x) dx$$` syntax |
| Tables | pandoc + CSS | Full GFM pipe-table support with professional styling |
| Code blocks | pandoc + CSS | Syntax highlighting via pandoc, monospace styling |
| Images | pandoc + Playwright | Local `file://` and remote `https://` images |
| Links | pandoc | Rendered as styled text |
| Lists / blockquotes | pandoc | Ordered, unordered, nested, blockquotes |
| YAML frontmatter | pandoc | `title` used as PDF title metadata |
| Footnotes | pandoc + CSS | `[^1]` syntax, rendered at page bottom |
| Strikethrough | pandoc | `~~deleted~~` syntax |
| Horizontal rules | pandoc + CSS | `---` rendered as styled separators |

## Prerequisites

| Dependency | Purpose | Install |
|---|---|---|
| `pandoc` | Markdown → HTML | `apt install pandoc` or `brew install pandoc` |
| `mmdc` (@mermaid-js/mermaid-cli) | Mermaid → SVG | `npm install -g @mermaid-js/mermaid-cli` |
| `katex` (npm) | LaTeX → HTML | `npm install -g katex` |
| `playwright` (Python) | HTML → PDF | `pip install playwright && playwright install chromium` |

Verify all dependencies are available before starting:

```bash
command -v pandoc && command -v mmdc && command -v katex && uv run python -c "from playwright.sync_api import sync_playwright; print('playwright OK')"
```

## Pipeline Steps

### Step 1: Mermaid rendering

Extract all ` ```mermaid ` code blocks from the markdown, render each to SVG, and replace the code blocks with inline SVG.

```bash
# Render a single mermaid block to SVG
mmdc -i diagram.mmd -o diagram.svg -t neutral --quiet
```

For each mermaid block:
1. Write the block content to a temp `.mmd` file
2. Run `mmdc -i temp.mmd -o temp.svg -t neutral`
3. Read the SVG output
4. Replace the original ` ```mermaid ... ``` ` block in the markdown with the raw `<svg>...</svg>` content

Skip this step if no mermaid blocks exist or use `--no-mermaid` mode.

### Step 2: Pandoc conversion

Convert the modified markdown (with inline SVGs) to standalone HTML5:

```bash
pandoc input_modified.md \
  --from markdown+yaml_metadata_block+footnotes+definition_lists+strikeout \
  --to html5 \
  --standalone \
  --katex \
  -o output.html
```

The `--katex` flag preserves LaTeX math as `<span class="math inline">` and `<span class="math display">` elements for Step 3.

### Step 3: KaTeX server-side rendering

Replace pandoc's math spans with fully rendered KaTeX HTML. This avoids needing client-side JavaScript in the PDF.

```javascript
// katex_render.js — Node.js script
const katex = require('katex');
const fs = require('fs');

let html = fs.readFileSync(process.argv[2], 'utf-8');

// Render display math
html = html.replace(
  /<span class="math display">\\\[([\s\S]*?)\\\]<\/span>/g,
  (_, tex) => katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false })
);

// Render inline math
html = html.replace(
  /<span class="math inline">\\\(([\s\S]*?)\\\)<\/span>/g,
  (_, tex) => katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false })
);

fs.writeFileSync(process.argv[2], html);
```

Run: `node katex_render.js output.html`

### Step 4: CSS injection

Inject professional document styles and KaTeX CSS into the HTML `<head>`. Key style rules:

```css
body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.6;
  color: #333;
  max-width: 100%;
  margin: 0;
  padding: 0;
}
h1 { font-size: 24pt; border-bottom: 2px solid #333; padding-bottom: 6pt; margin-top: 24pt; }
h2 { font-size: 18pt; border-bottom: 1px solid #ccc; padding-bottom: 4pt; margin-top: 20pt; }
h3 { font-size: 14pt; margin-top: 16pt; }
table { border-collapse: collapse; width: 100%; margin: 12pt 0; }
th { background: #f5f5f5; font-weight: 600; text-align: left; }
th, td { border: 1px solid #ddd; padding: 6pt 10pt; }
pre { background: #f8f8f8; border: 1px solid #e0e0e0; border-radius: 3pt; padding: 10pt; overflow-x: auto; font-size: 9pt; }
code { font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; }
blockquote { border-left: 3pt solid #ddd; padding-left: 12pt; color: #666; margin: 12pt 0; }
img, svg { max-width: 100%; height: auto; }

@media print {
  body { font-size: 10pt; }
  pre { white-space: pre-wrap; word-wrap: break-word; }
}
```

Also inject the KaTeX CSS (from `node_modules/katex/dist/katex.min.css` or CDN) with local font paths.

### Step 5: Playwright PDF export

```python
from playwright.sync_api import sync_playwright

def html_to_pdf(html_path, pdf_path, format="A4", landscape=False, margin="0.75in", header_footer=False):
    margins = parse_margins(margin)  # parse "0.75in" or "top,right,bottom,left"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path}", wait_until="networkidle")
        page.pdf(
            path=pdf_path,
            format=format,
            landscape=landscape,
            margin=margins,
            print_background=True,
            display_header_footer=header_footer,
            footer_template='<div style="font-size:8pt; text-align:center; width:100%;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' if header_footer else "",
        )
        browser.close()
```

## Conversion Options

| Parameter | Default | Description |
|---|---|---|
| `format` | `A4` | Page size: `A4`, `Letter`, `Legal`, `A3` |
| `margin` | `0.75in` | Margins — single value (uniform) or `top,right,bottom,left` |
| `landscape` | `false` | Landscape orientation |
| `header_footer` | `false` | Show page numbers in footer (page / total) |
| `custom_css` | none | Path to additional CSS file to layer on top |
| `no_mermaid` | `false` | Skip Mermaid rendering (keeps raw code blocks) |
| `no_math` | `false` | Skip KaTeX math rendering |

## Mermaid Theming

Set a `.mermaidrc` JSON config file:

```json
{
  "theme": "neutral",
  "themeVariables": {
    "primaryColor": "#e1f5fe",
    "lineColor": "#333"
  }
}
```

Pass to mmdc: `mmdc -i input.mmd -o output.svg -c .mermaidrc`

## Custom CSS

Layer custom CSS on top of the default styles. Custom rules take precedence.

Example dark theme:

```css
body { background: #1a1a2e; color: #e0e0e0; }
h1, h2, h3 { color: #e0e0e0; border-color: #444; }
table th { background: #2a2a4a; }
pre { background: #0d0d1a; border-color: #333; }
```

## Error Handling

| Symptom | Likely Cause | Fix |
|---|---|---|
| "mmdc FAILED" in Mermaid step | Invalid Mermaid syntax | Check diagram syntax; mmdc stderr has the parse error |
| Raw LaTeX visible in PDF | KaTeX couldn't parse expression | Check LaTeX syntax; KaTeX falls back gracefully |
| "No Chrome binary found" | Playwright Chromium missing | Run `playwright install chromium` |
| Blank/missing diagrams | SVG too large or complex | Try `--no-mermaid` and render diagrams separately |
| Images not loading | Relative paths broken | Use absolute paths or `file://` URIs |
| Page breaks in wrong places | No explicit break markers | Add `<div style="page-break-before: always"></div>` in markdown |

## Limitations

- **Mermaid diagram rendering** requires either network access for CDN-based mmdc or a local `@mermaid-js/mermaid-cli` install.
- **Large documents** (100+ pages or many high-resolution images) may hit Playwright's memory limits. Split into multiple input files and merge the resulting PDFs.
- **Page breaks** require explicit CSS markers (`page-break-before: always`) or manual `<div>` in the source. Pandoc does not infer page breaks from heading structure.
- **KaTeX coverage** is broad but not complete — obscure LaTeX macros or packages not in KaTeX's supported set will fail and fall back to raw LaTeX.
- **Custom CSS** may render differently across PDF viewers — layout is determined by Chromium at render time.
