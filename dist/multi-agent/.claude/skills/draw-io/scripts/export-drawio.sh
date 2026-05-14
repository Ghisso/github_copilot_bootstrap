#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 path/to/diagram.drawio" >&2
  exit 1
fi

diagram_path="$1"

if [[ ! -f "$diagram_path" ]]; then
  echo "File not found: $diagram_path" >&2
  exit 1
fi

if [[ "${diagram_path##*.}" != "drawio" ]]; then
  echo "Expected a .drawio file: $diagram_path" >&2
  exit 1
fi

base_path="${diagram_path%.drawio}"
svg_path="${base_path}.svg"
png_path="${base_path}.png"

if command -v drawio >/dev/null 2>&1; then
  drawio -x -f svg -o "$svg_path" "$diagram_path"
  drawio -x -f png -s 2 -t -o "$png_path" "$diagram_path"
  echo "Exported: $svg_path"
  echo "Exported: $png_path"
  exit 0
fi

cat <<EOF
No draw.io CLI found in this environment.

Manual export steps:
1. Open: $diagram_path
2. Export SVG to: $svg_path
3. Export PNG to: $png_path
4. Keep the same basename beside the source file
EOF