# Draw.io Skill

This skill standardizes diagram work in this repository with a `.drawio`-first workflow.

## What It Covers

- source-of-truth editing in `.drawio`
- explicit font settings for diagrams and slide use
- coordinate-based layout adjustments
- arrow layering and label clearance rules
- frame padding and overflow prevention
- export discipline for sibling `.svg` and `.png` files
- final review checklist before considering a diagram done

## Repository Convention

Store source diagrams in `docs/drawio/` and keep exports beside them with the same basename.

```text
docs/drawio/diagram_name.drawio
docs/drawio/diagram_name.svg
docs/drawio/diagram_name.png
```

## Included References

- `references/layout-guidelines.md` for spacing, padding, and alignment rules
- `references/aws-icons.md` for optional cloud-icon guidance
- `scripts/export-drawio.sh` for local export or fallback instructions

## Manual Export Note

This dev container may not include `drawio` or raster export tooling. In that case, the workflow is still:

1. Create or edit the `.drawio` source here.
2. Export manually in diagrams.net or draw.io desktop.
3. Save `.svg` and `.png` beside the source with the same basename.