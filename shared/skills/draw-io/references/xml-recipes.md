# Draw.io XML Recipes

Worked XML examples and tool-specific instructions that back the rules in the
root `SKILL.md` and in `references/layout-guidelines.md`. The root file states
the rule; this file has the exact syntax.

## Font XML Pattern

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

Rule: set `defaultFontFamily` in `mxGraphModel`; also set `fontFamily` in text
styles for important labels and titles; prefer body text around 16px to 18px
and titles 24px+.

## Export Commands

`drawio` CLI is often unavailable in containerized or restricted environments.
Export is optional — the `.drawio` file is the permanent source of truth.

### If CLI is available

```bash
drawio -x -f svg -o docs/drawio/name.svg docs/drawio/name.drawio
drawio -x -f png -s 2 -t -o docs/drawio/name.png docs/drawio/name.drawio
```

PNG options: `-s 2` (2x scale), `-t` (transparent), `-x` (export mode)

### If CLI is not available

**Recommended: use online draw.io** (fastest, no installation needed):
1. Visit https://app.diagrams.net
2. File -> Open -> select the `.drawio` file
3. File -> Export As -> SVG/PNG
4. Check "Transparent background" (for PNG, check "2x scale" for high-DPI)
5. Save beside the source with the same basename

**Alternative: VS Code draw.io extension**
- Install the draw.io extension
- Right-click `.drawio` file -> "Edit with Draw.io"
- Ctrl+Shift+E (or menu) to export

### Helper script

```bash
bash .claude/skills/draw-io/scripts/export-drawio.sh docs/drawio/name.drawio
```

This script checks for CLI availability and provides manual export
instructions if needed.

## Coordinate Adjustment Steps

1. Open the `.drawio` file as XML if precise positioning is needed.
2. Find the relevant `mxCell`, usually by `id` or `value`.
3. Adjust the `mxGeometry` attributes:
   - `x`: distance from left
   - `y`: distance from top
   - `width`: element width
   - `height`: element height
4. Export and visually verify.

## Coordinate Calculations

- Element vertical center is `y + (height / 2)`.
- Align multiple cards by matching top edges or center coordinates.
- Use 20px or 40px grid increments (rhythm) for all coordinates instead of
  arbitrary values.
- All nodes in a row should have consistent y-coordinate spacing (e.g.,
  y=410, 455, 500 rather than y=400, 443, 492).

Example:

```text
Card A: y=180, height=80 -> center=220
Card B: y should satisfy y + (height / 2) = 220

Rhythm Example:
Node sequence: x=40, 320, 640, 960 (280-320px increments)
All y-coordinates: multiples of 5px (410, 455, 500, 540, etc.)
```

## Container Margin Rule

Maintain at least **30px margin** from container (lane, frame) boundaries.
Stroke width consumes additional pixels, especially for rounded corners.

Example:

```text
Frame: y=20, height=400 -> range 20-420
Safe top for internal content: y >= 50 (30px margin below frame top)
Safe bottom for internal content: y <= 390 (30px margin above frame bottom)
```

**Critical for rounded containers**: the visible inner area is smaller than
the raw geometry due to stroke rendering. Test in the exported image.

## Grid Alignment and Orthogonal Routing

For presentation-quality diagrams (especially multi-lane architectures):

**Coordinates on rhythm:**
- All node X-coordinates should follow a consistent increment pattern (e.g.,
  40, 320, 640, 960 or 200, 600, 1000, 1400).
- All node Y-coordinates should snap to 5px or 10px increments.
- Lanes themselves should span y-coordinates aligned to round numbers (e.g.,
  y=80, 360, 700 for a 3-lane diagram).

**Orthogonal connector routing (L-shaped):**
- Replace diagonal arrows with orthogonal paths using strategic waypoints.
- Waypoints should route around node clusters and avoid cutting through
  lanes.
- Use vertical waypoints for fan-out routing (e.g., all branches split at the
  same x-coordinate).
- Use horizontal waypoints for feedback loops to avoid layer crossings
  (route through gaps between lanes).
- Minimize waypoint count: every waypoint should serve a purpose (avoiding
  overlap or changing direction).

**Example: feedback arc routing**

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

Benefit: reduces visual clutter from crossing arrows; makes data flow
unmistakable.

## Text Width for Multilingual Content

Japanese text needs noticeably more horizontal room per character than Latin
text:

- allow roughly 30px to 40px per Japanese character
- when width is too narrow, line breaks become unpredictable

Example:

```xml
<mxGeometry x="140" y="60" width="400" height="40" />
```

## Arrow Placement

Arrows should sit on the back layer so they do not visually cut through
cards.

In XML ordering terms, place arrow cells immediately after titles or early in
the section, before the foreground cards:

```xml
<mxCell id="title" value="..." .../>
<mxCell id="arrow1" style="edgeStyle=..." edge="1" .../>
<mxCell id="box1" .../>
```

Rules:
- keep arrows behind content when possible
- keep labels off the arrow line
- keep arrow endpoints at least 20px away from label bottoms or card edges

## Arrow Connections to Text Labels

When connecting to text elements, `exitX` and `exitY` are often unreliable.
Use explicit source and target points instead.

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

## edgeLabel Offset Adjustment

Move edge labels away from the connector using `offset`.

```xml
<mxPoint x="0" y="-40" as="offset"/>
```

Use:
- negative `y` to move the label above the line
- positive `y` to move the label below the line

## Background Frames and Internal Element Placement

One of the most important layout rules: size the frame to leave margin for
its label, not just its content.

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

## Diagram Metadata

When useful, include diagram metadata in a footer note or title area:
- title
- short description
- last updated
- author
- version

## Presentation Note (Quarto / Reveal.js)

If a diagram is being embedded into Reveal.js slides through Quarto:

```yaml
---
format:
  revealjs:
    auto-stretch: false
---
```

This reduces layout distortion for exported diagram images.
