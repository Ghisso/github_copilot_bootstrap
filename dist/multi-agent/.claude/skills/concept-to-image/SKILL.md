---
name: concept-to-image
description: |
  Turn any concept, idea, or description into a polished static HTML visual,
  then export it as a PNG or SVG image file. Use when:
  - "create an image of", "concept to image", "turn this into an image"
  - "design a graphic", "make a diagram", "infographic"
  - "export as PNG", "save as SVG", "screenshot this HTML"
  - Creating concept diagrams, flowcharts, comparison charts, process visuals,
    educational diagrams, social media graphics, data visualizations, posters,
    cards, badges, icons, or any "make me an image of X" request achievable
    with HTML/CSS/SVG rather than photographic AI generation.
  For interactive HTML visuals viewed in a browser, consider building directly.
  For slide decks, use html-presentation instead.
---

# Concept to Image

Creates polished visuals from concepts using HTML/CSS/SVG as a refineable intermediate, then exports to PNG or SVG.

## Why HTML as intermediate

HTML is the refineable layer between idea and image. Unlike direct canvas rendering, the user can see the HTML artifact, request changes ("make the title bigger", "swap the colors", "add a third column"), and only export once satisfied. This makes the workflow iterative and controllable.

## Workflow

```text
Concept → HTML artifact (view + refine) → PNG or SVG export
```

1. **Interpret** the user's concept — determine what kind of visual best fits (diagram, infographic, card, chart, etc.)
2. **Design** a self-contained HTML file using inline CSS and inline SVG — zero external dependencies
3. **Present** the HTML so the user can preview and request refinements
4. **Iterate** on the HTML based on user feedback (colors, layout, content, sizing)
5. **Export** to PNG and/or SVG when the user is satisfied

## Step 1: Interpret the concept

Determine the best visual format:

| User intent | Visual format | Approach |
|---|---|---|
| Explain a process/flow | Flowchart or pipeline diagram | SVG paths + boxes |
| Compare items | Side-by-side or matrix | CSS Grid |
| Show hierarchy | Tree or layered diagram | Nested containers + SVG connectors |
| Present data | Chart or infographic | SVG shapes + data labels |
| Social/marketing graphic | Card or poster | Typography-forward HTML/CSS |
| Icon, logo, badge | Compact symbol | Pure SVG |
| Educational concept | Annotated diagram | SVG + positioned labels |

### Sizing guidelines

| Use case | Recommended size |
|---|---|
| Social media graphic | 1200×630 |
| Infographic (portrait) | 800×1200 |
| Presentation slide | 1920×1080 |
| Square post | 1080×1080 |
| Icon/badge | 256×256 or 512×512 |
| Wide diagram | 1600×900 |

Set the `.canvas` container to the chosen size.

## Step 2: Design the HTML

Core rules:

- **Single file, self-contained**: All CSS inline in `<style>`, all graphics as inline `<svg>`. No external resources.
- **Fixed viewport**: Set explicit `width` and `height` on the root container matching the intended export size.
- **Anti-AI-slop**: Avoid centered-everything layouts, purple gradients, uniform rounded corners, and Inter/system font defaults. See design anti-patterns below.
- **SVG-first for shapes**: Use inline SVG for icons, connectors, shapes, and any element that should scale cleanly. CSS for layout and typography.
- **Color with intention**: 3-4 hues max + neutrals. Define as CSS custom properties. Every color encodes meaning.

### Design anti-patterns to avoid

These produce generic "AI-generated" looking output:

- Centered everything with equal spacing
- Purple/blue gradient backgrounds
- Uniform border-radius on all elements
- Generic icon libraries (use custom inline SVG)
- System font stack without typographic intention
- Drop shadows on everything
- Low information density (too much whitespace)

### Font handling

Use web-safe font stacks with intentional fallbacks:

- **Technical/mono**: `'Courier New', 'Consolas', monospace`
- **Clean sans**: `'Helvetica Neue', 'Arial', sans-serif`
- **Editorial serif**: `'Georgia', 'Times New Roman', serif`
- **Display**: Use SVG text with custom paths for display typography when needed

### HTML template

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
      --color-bg: #f8f6f2;
      --color-primary: #2d3436;
      --color-accent: #e17055;
      --color-secondary: #74b9ff;
      --color-text: #2d3436;
    }
    .canvas {
      width: 1200px;
      height: 630px;
      background: var(--color-bg);
      font-family: 'Helvetica Neue', Arial, sans-serif;
      position: relative;
      overflow: hidden;
    }
    /* Layout and component styles here */
  </style>
</head>
<body>
  <div class="canvas">
    <!-- Content here -->
  </div>
</body>
</html>
```

## Step 3: Present and iterate

Present the HTML file to the user. Common refinement requests:

- Color/theme changes → update CSS custom properties
- Layout adjustments → modify grid/flexbox
- Content changes → edit text/SVG elements
- Size changes → update `.canvas` dimensions

Each iteration is a quick HTML edit, not a full re-render.

## Step 4: Export to image

Once the user is satisfied, export using one of these approaches:

### Option A: Playwright (Python)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{html_path}")
    element = page.query_selector(".canvas")
    element.screenshot(path="output.png", scale="device")
    browser.close()
```

### Option B: Browser screenshot

Open the HTML file in a browser and use DevTools to screenshot the `.canvas` element at the desired resolution.

### PNG export

Uses headless browser to screenshot the `.canvas` element at the specified scale factor. Scale 2 produces retina-quality output (e.g., 1200×630 CSS pixels → 2400×1260 PNG).

### SVG export

Two strategies:

1. **SVG-native content**: If the `.canvas` element contains a single root `<svg>`, extract it directly as a clean SVG file. This produces a true vector SVG.
2. **HTML-based content**: If the content is CSS/HTML-heavy, falls back to PNG export. True SVG requires SVG-native design.

### Delivering the output

Present both the HTML (for future editing) and the image (final output).

## Error Handling

| Error | Cause | Resolution |
|---|---|---|
| Playwright not found | Package not installed | Run `pip install playwright && playwright install chromium` |
| Browser launch failure | Headless Chromium fails to start | Verify headless mode is supported; check available memory |
| `.canvas` selector not found | HTML does not contain matching element | Verify the root container has `class="canvas"` |
| SVG export falls back to PNG | `.canvas` contains HTML/CSS, not a root SVG | Redesign with a single root `<svg>` if vector output is required |

## Limitations

- **Playwright + Chromium required** for PNG export — install separately.
- **SVG export is best-effort** — complex HTML/CSS layouts fall back to PNG.
- **Max viewport 4096×4096** — Chromium limit. Use scale factor for higher effective resolution.
- **No animation support** — exported images are static snapshots.
- **Font availability** — system fonts only unless embedded as base64.
