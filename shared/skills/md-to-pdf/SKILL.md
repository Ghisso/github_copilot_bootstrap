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

## Prerequisites

Verify all dependencies are available before starting:

```bash
command -v pandoc && command -v mmdc && command -v katex && uv run python -c "from playwright.sync_api import sync_playwright; print('playwright OK')"
```

See `references/features-and-options.md` for the install command for each
dependency and the full feature-to-rendering-engine matrix.

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

## Options, Customization, and Troubleshooting

- Conversion parameters (`format`, `margin`, `landscape`, `header_footer`, `custom_css`, `no_mermaid`, `no_math`): see `references/features-and-options.md`.
- Mermaid theming and layered custom CSS: see `references/customization-and-troubleshooting.md`.
- Common failure symptoms and fixes: see `references/customization-and-troubleshooting.md`.

## Limitations

- **Mermaid diagram rendering** requires either network access for CDN-based mmdc or a local `@mermaid-js/mermaid-cli` install.
- **Large documents** (100+ pages or many high-resolution images) may hit Playwright's memory limits. Split into multiple input files and merge the resulting PDFs.
- **Page breaks** require explicit CSS markers (`page-break-before: always`) or manual `<div>` in the source. Pandoc does not infer page breaks from heading structure.
- **KaTeX coverage** is broad but not complete — obscure LaTeX macros or packages not in KaTeX's supported set will fail and fall back to raw LaTeX.
- **Custom CSS** may render differently across PDF viewers — layout is determined by Chromium at render time.

## References in This Skill

- `references/features-and-options.md` — supported feature matrix, dependency install commands, and conversion parameter reference
- `references/customization-and-troubleshooting.md` — Mermaid theming, custom CSS, and the error-handling table
