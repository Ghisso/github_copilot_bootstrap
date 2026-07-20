---
name: draw-io
visibility: public
description: |
  Create, edit, and polish draw.io or diagrams.net diagrams with a `.drawio`-first
  workflow. Use when:
  - "draw.io", "drawio", or "diagrams.net" diagrams are requested
  - The user wants a new `.drawio` file in `docs/drawio/`
  - A diagram needs cleaner layout, spacing, alignment, or export preparation
  - The task mentions best practices, design principles, layout adjustment, checklist, SVG export, or PNG export
  - The user wants a consistent architecture or flow diagram style across the repo
---

# Draw.io Diagram Skill

This skill is for creating and maintaining repository diagrams with draw.io or diagrams.net as the source of truth. It is intentionally `.drawio`-first: edits happen in the XML-backed source file, then sibling export files are produced in the same folder with the same basename.

## Purpose

Use this skill to:

- create or edit `.drawio` XML diagram files
- improve spacing, alignment, and consistency programmatically
- refine layout with orthogonal (L-shaped) connector routing and grid-aligned coordinates
- prepare diagrams for documentation or slide use
- enforce layout, readability, and review standards
- optionally export `.svg` and `.png` files next to the source (drawio CLI not always available)

## Basic Rules

- Edit only the `.drawio` source file.
- Do not treat `.svg` or `.png` as the editable master.
- Keep export files beside the source with the same basename (when available).
- Prefer transparent or theme-neutral backgrounds for documentation reuse.
- Reuse one visual system per diagram: same font family, corner radius, stroke width, and spacing rhythm.
- Export is optional: diagrams are always valid and editable in draw.io regardless of export status.

Repository convention:

```text
docs/drawio/name.drawio
docs/drawio/name.svg
docs/drawio/name.png
```

## Font Settings

The external references are explicit here: set the model font and the element font, not just one of them.

Default repo guidance:

- use `Helvetica` or a consistent sans-serif family for general repository diagrams
- if the diagram is intended for Quarto slides or includes Japanese text, prefer `Noto Sans JP`

Example:

```xml
<mxGraphModel defaultFontFamily="Noto Sans JP" ...>
```

And explicitly on text cells:

```xml
<mxCell
  value="API"
  style="text;html=1;fontSize=18;fontFamily=Noto Sans JP;"
  vertex="1"
  parent="1"
/>
```

Rule:

- set `defaultFontFamily` in `mxGraphModel`
- also set `fontFamily` in text styles for important labels and titles
- prefer body text around 16px to 18px and titles 24px+

## Export (Optional)

Note: `drawio` CLI is often unavailable in containerized or restricted environments. Export is **optional**—the `.drawio` file is the permanent source of truth.

### If CLI is available:

```bash
drawio -x -f svg -o docs/drawio/name.svg docs/drawio/name.drawio
drawio -x -f png -s 2 -t -o docs/drawio/name.png docs/drawio/name.drawio
```

PNG options: `-s 2` (2x scale), `-t` (transparent), `-x` (export mode)

### If CLI not available:

**Recommended: Use online draw.io** (fastest, no installation needed):
1. Visit https://app.diagrams.net
2. File → Open → select the `.drawio` file
3. File → Export As → SVG/PNG
4. Check "Transparent background" (for PNG, check "2x scale" for high-DPI)
5. Save beside the source with the same basename

**Alternative: VS Code draw.io Extension**
- Install the draw.io extension
- Right-click `.drawio` file → "Edit with Draw.io"
- Ctrl+Shift+E (or menu) to export

### Helper Script

```bash
bash .claude/skills/draw-io/scripts/export-drawio.sh docs/drawio/name.drawio
```

This script checks for CLI availability and provides manual export instructions if needed.

## Layout Adjustment

### Coordinate Adjustment Steps

1. Open the `.drawio` file as XML if precise positioning is needed.
2. Find the relevant `mxCell`, usually by `id` or `value`.
3. Adjust the `mxGeometry` attributes:
   - `x`: distance from left
   - `y`: distance from top
   - `width`: element width
   - `height`: element height
4. Export and visually verify.

### Coordinate Calculations

- Element vertical center is `y + (height / 2)`.
- Align multiple cards by matching top edges or center coordinates.
- Use 20px or 40px grid increments (rhythm) for all coordinates instead of arbitrary values.
- All nodes in a row should have consistent y-coordinate spacing (e.g., y=410, 455, 500 rather than y=400, 443, 492).

Example:

```text
Card A: y=180, height=80 -> center=220
Card B: y should satisfy y + (height / 2) = 220

Rhythm Example:
Node sequence: x=40, 320, 640, 960 (280-320px increments)
All y-coordinates: multiples of 5px (410, 455, 500, 540, etc.)
```

### Container Margin Rule

Maintain at least **30px margin** from container (lane, frame) boundaries. Stroke width consumes additional pixels, especially for rounded corners.

Example:

```text
Frame: y=20, height=400 -> range 20–420
Safe top for internal content: y >= 50 (30px margin below frame top)
Safe bottom for internal content: y <= 390 (30px margin above frame bottom)
```

**Critical for rounded containers**: the visible inner area is smaller than the raw geometry due to stroke rendering. Test in the exported image.

### Grid Alignment & Orthogonal Routing

For presentation-quality diagrams (especially multi-lane architectures):

**Coordinates on rhythm:**
- All node X-coordinates should follow a consistent increment pattern (e.g., 40, 320, 640, 960 or 200, 600, 1000, 1400).
- All node Y-coordinates should snap to 5px or 10px increments.
- Lanes themselves should span y-coordinates aligned to round numbers (e.g., y=80, 360, 700 for 3-lane diagram).

**Orthogonal connector routing (L-shaped):**
- Replace diagonal arrows with orthogonal paths using strategic waypoints.
- Waypoints should route around node clusters and avoid cutting through lanes.
- Use vertical waypoints for fan-out routing (e.g., all branches split at same x-coordinate).
- Use horizontal waypoints for feedback loops to avoid layer crossings (route through gaps between lanes).
- Minimize waypoint count: every waypoint should serve a purpose (avoiding overlap or changing direction).

**Example: Feedback arc routing**
```xml
<!-- Route feedback above a lane boundary to avoid crossing nodes -->
<mxCell id="feedback" source="bottom_node" target="upper_node" edge="1">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="1500" y="50"/>  <!-- Exit source -->
      <mxPoint x="1500" y="gap_y"/>  <!-- Rise above lane -->
      <mxPoint x="target_x" y="gap_y"/>  <!-- Horizontal to target -->
    </Array>
  </mxGeometry>
</mxCell>
```

Benefit: Reduces visual clutter from crossing arrows; makes data flow unmistakable.

## Design Principles

### Basic Principles

- Clarity: keep diagrams simple and visually clean
- Consistency: unify colors, fonts, icon sizes, and line thickness
- Accuracy: do not sacrifice correctness for cosmetic simplification

### Element Rules

- Label all important elements
- Use arrows to indicate direction
- Prefer two unidirectional arrows over one bidirectional arrow when direction matters
- Add a legend if any symbol or line style is not self-evident
- If using cloud diagrams, prefer official service names and current icon sets

### Accessibility

- Ensure sufficient color contrast
- Do not encode meaning by color alone
- Use labels, line styles, or patterns in addition to color

### Progressive Disclosure

For complex systems, split the work into staged diagrams instead of one overloaded canvas:

1. Context diagram
2. System diagram
3. Component diagram
4. Deployment diagram
5. Data flow diagram
6. Sequence diagram

### Metadata

When useful, include diagram metadata in a footer note or title area:

- title
- short description
- last updated
- author
- version

## Best Practices

### Transparent Backgrounds

Do not force a white page background unless the output explicitly needs it.

Avoid:

```xml
<mxGraphModel background="#ffffff" ...>
```

Prefer:

```xml
<mxGraphModel page="1" background="none" ...>
```

### Font Size

- Use roughly 1.5x standard UI sizing for documentation and slide readability.
- As a working rule, keep body text around 18px when the diagram is meant to be read from exported images.

### Text Width Calculation

The referenced skills explicitly call out Japanese text width. Keep this note because it matters for multilingual diagrams:

- allow roughly 30px to 40px per Japanese character
- when width is too narrow, line breaks become unpredictable

Example:

```xml
<mxGeometry x="140" y="60" width="400" height="40" />
```

### Arrow Placement

Arrows should sit on the back layer so they do not visually cut through cards.

In XML ordering terms, place arrow cells immediately after titles or early in the section, before the foreground cards:

```xml
<mxCell id="title" value="..." .../>
<mxCell id="arrow1" style="edgeStyle=..." edge="1" .../>
<mxCell id="box1" .../>
```

Rules:

- keep arrows behind content when possible
- keep labels off the arrow line
- keep arrow endpoints at least 20px away from label bottoms or card edges

### Arrow Connections to Text Labels

When connecting to text elements, `exitX` and `exitY` are often unreliable. Use explicit source and target points instead.

Example:

```xml
<mxCell id="arrow" style="..." edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="1279" y="500" as="sourcePoint"/>
    <mxPoint x="119" y="500" as="targetPoint"/>
    <Array as="points">
      <mxPoint x="1279" y="560"/>
      <mxPoint x="119" y="560"/>
    </Array>
  </mxGeometry>
</mxCell>
```

### edgeLabel Offset Adjustment

Move edge labels away from the connector using `offset`.

Example:

```xml
<mxPoint x="0" y="-40" as="offset"/>
```

Use:

- negative `y` to move the label above the line
- positive `y` to move the label below the line

### Remove Unnecessary Elements

- remove decorative items that do not add meaning
- do not duplicate concepts already represented by another shape or icon
- prefer fewer, more readable elements over crowded completeness

### Labels and Headings

- service name only: one line
- service name plus supporting detail: two lines maximum
- **use `&lt;br&gt;` (XML-escaped) for deliberate line breaks** — NOT raw `<br>` (breaks XML parsing)
- shorten redundant wording when the icon or context already conveys it

**HTML Line Break Escaping:**
Inside XML attributes, HTML tags must be XML-escaped:

Wrong (breaks parser):
```xml
<mxCell value="Line 1<br>Line 2" ... />
```

Correct (safe):
```xml
<mxCell value="Line 1&lt;br&gt;Line 2" ... />
```

### Background Frames and Internal Element Placement

This is one of the most important layout rules from the references.

Bad:

```xml
<mxCell id="bg" style="rounded=1;strokeWidth=3;...">
  <mxGeometry x="500" y="20" width="560" height="400" />
</mxCell>
<mxCell id="label" value="Title" style="text;...">
  <mxGeometry x="510" y="30" width="540" height="35" />
</mxCell>
```

Better:

```xml
<mxCell id="bg" style="rounded=1;strokeWidth=3;...">
  <mxGeometry x="500" y="20" width="560" height="430" />
</mxCell>
<mxCell id="label" value="Title" style="text;...">
  <mxGeometry x="510" y="50" width="540" height="35" />
</mxCell>
```

Rules:

- maintain 30px+ margin inside frames
- account for rounded corners and stroke width
- visually verify exports for overflow or clipping

## Presentation Note

If a diagram is being embedded into Reveal.js slides through Quarto, the references recommend:

```yaml
---
format:
  revealjs:
    auto-stretch: false
---
```

This reduces layout distortion for exported diagram images.

## Checklist

- `.drawio` source edited first
- sibling exports created (if CLI/tools available) with same basename
- no solid white background unless explicitly required
- font size is readable at document or slide scale
- `defaultFontFamily` and element `fontFamily` are set consistently where needed
- **coordinates follow 20/40px grid rhythm** (no arbitrary values)
- arrows are on the back layer (declared in XML before boxes)
- **arrow routing is orthogonal (L-shaped)** where visual clarity matters
- arrow labels do not overlap connectors
- arrow endpoints have 20px+ clearance from labels or card edges
- arrows do not penetrate cards or icons in the exported image
- internal elements have 30px+ margin from frame boundaries
- **HTML line breaks use `&lt;br&gt;` (XML-escaped), not raw `<br>`**
- no clipped text or overflow in the export
- no unnecessary decorative elements remain
- exported SVG and PNG have been visually verified (or documented with export instructions)

## References in This Skill

- `references/layout-guidelines.md`
- `references/aws-icons.md`
- `.claude/skills/draw-io/scripts/export-drawio.sh`