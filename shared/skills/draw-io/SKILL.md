---
name: draw-io
visibility: public
description: |
  Create, edit, and polish draw.io or diagrams.net diagrams with a `.drawio`-first
  workflow. Use when:
  - "draw.io", "drawio", or "diagrams.net" diagrams are requested
  - The user wants a new `.drawio` file in `docs/drawio/`
  - A diagram needs cleaner layout, spacing, alignment, or export preparation
  - The task mentions diagram layout adjustment, a pre-export diagram checklist, or SVG/PNG export
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

## Fonts and Export

- Set `defaultFontFamily` on `mxGraphModel` and `fontFamily` on important text and title cells.
- Default to `Helvetica` or another consistent sans-serif; use `Noto Sans JP` for Japanese text or for Quarto/Reveal.js slides.
- Export is optional — the `.drawio` file is always the valid, editable source of truth regardless of export status.
- See `references/xml-recipes.md` for the exact font XML pattern and for CLI, online, and VS Code export instructions.

## Layout and Spacing

- Follow the coordinate, spacing, typography, and connector rules in `references/layout-guidelines.md`.
- Maintain at least 30px margin inside frames and containers. Rounded corners and stroke width shrink the usable inner area further than the raw geometry suggests — verify against the exported image.
- See `references/xml-recipes.md` for worked coordinate, grid-alignment, orthogonal-routing, and frame-margin XML examples.

## Design Principles

### Basic Principles

- Clarity: keep diagrams simple and visually clean
- Consistency: unify colors, fonts, icon sizes, and line thickness
- Accuracy: do not sacrifice correctness for cosmetic simplification

### Element Rules

- Label all important elements
- Use arrows to indicate direction; prefer two unidirectional arrows over one bidirectional arrow when direction matters
- Add a legend if any symbol or line style is not self-evident
- If using cloud diagrams, prefer official service names and current icon sets (see `references/aws-icons.md` for AWS-specific guidance)
- Remove decorative items that do not add meaning; prefer fewer, more readable elements over crowded completeness

### Accessibility

- Ensure sufficient color contrast
- Do not encode meaning by color alone — use labels, line styles, or patterns in addition to color

### Staged Diagrams for Complex Systems

For complex systems, split the work into staged diagrams instead of one overloaded canvas: context diagram, system diagram, component diagram, deployment diagram, data flow diagram, sequence diagram.

## Labels, Headings, and XML Safety

- service name only: one line; service name plus supporting detail: two lines maximum
- shorten redundant wording when the icon or context already conveys it
- **use `&lt;br&gt;` (XML-escaped) for deliberate line breaks — NOT raw `<br>` (breaks XML parsing)**

Wrong (breaks parser):

```xml
<mxCell value="Line 1<br>Line 2" ... />
```

Correct (safe):

```xml
<mxCell value="Line 1&lt;br&gt;Line 2" ... />
```

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

- `references/layout-guidelines.md` — spacing, coordinate, typography, and connector rules
- `references/xml-recipes.md` — font/export XML patterns, worked layout and arrow XML examples, and Quarto/Reveal.js embedding notes
- `references/aws-icons.md` — optional AWS icon guidance
- `.claude/skills/draw-io/scripts/export-drawio.sh`
