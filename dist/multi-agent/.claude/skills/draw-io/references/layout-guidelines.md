# Draw.io Layout Guidelines

## Canvas

- Prefer 16:9 pages for architecture or workflow overviews.
- Keep at least 20px outer margin around the composition.
- Reserve clear bands for title, main content, and optional footer or legend.

## Spacing System

- Small gap: 20px
- Standard gap: 40px
- Section padding: 30px minimum
- Large separation between zones: 60px+

## Coordinate Rules

- Use 20px or 40px increments where practical.
- Vertical center formula: `y + (height / 2)`.
- Match either top edges or center coordinates for sibling cards.
- Increase container size before shrinking text to solve crowding.

## Typography

- Title: 28px to 32px bold
- Section title: 18px to 20px bold
- Body: 16px to 18px
- Footer or caption: 12px to 14px
- For slide or multilingual use, set both `defaultFontFamily` and per-element `fontFamily`

## Containers

- Use large rounded containers for major sections.
- Use white or near-white cards inside colored sections for readability.
- Keep at least 30px inner margin from frame boundaries.
- Remember that rounded corners reduce safe visual space.

## Connectors

- Use solid connectors for primary flow.
- Use dashed connectors for secondary relationships or annotations.
- Put arrows behind content when possible.
- Keep labels at least 20px away from the line.
- Use explicit `sourcePoint` and `targetPoint` when text-element connections are unreliable.

## XML Ordering Rule

- Title first
- Background or section arrows next when they should sit on the back layer
- Foreground boxes and cards after that

This ordering improves exported readability because connectors do not cut across cards.

## Review Pass

- Zoom out and verify balance, whitespace, and section rhythm.
- Zoom in and verify text wrapping, padding, and connector endpoints.
- Check exported output for clipping, overlap, and line-label collisions.
- Confirm the diagram still reads when embedded in documentation.