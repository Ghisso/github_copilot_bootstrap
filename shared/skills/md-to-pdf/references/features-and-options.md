# Markdown to PDF — Features, Dependencies, and Options

Reference tables that support the root `SKILL.md` procedure. The root file
has the five conversion steps; this file has the parameter and dependency
detail.

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
