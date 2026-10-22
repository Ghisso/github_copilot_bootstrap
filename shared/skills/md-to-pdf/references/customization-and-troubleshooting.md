# Markdown to PDF — Customization and Troubleshooting

Secondary workflows that most conversions do not need: Mermaid theming,
layered custom CSS, and the common failure table.

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

Layer custom CSS on top of the default styles from Step 4 of the root
procedure. Custom rules take precedence.

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
