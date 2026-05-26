# img2pptx

Codex skill for converting slide images into high-fidelity, maximally editable PowerPoint decks.

`img2pptx` rebuilds ordinary text, rich text runs, simple shapes, and lines as editable PPT objects. It extracts only artistic typography, unsupported fonts, photos, icons, generated art, ornaments, and other complex visuals as independent PNG assets.

## Features

- Converts one or more slide screenshots or exported slide images into `.pptx`.
- Keeps ordinary text editable whenever a close font is available.
- Supports mixed-color editable text through layout `runs`.
- Rebuilds simple geometry as native PowerPoint shapes and lines.
- Extracts artistic text and complex visuals as transparent PNG assets.
- Generates contact sheets, asset placement reports, preview PNGs, and visual diff reports.
- Supports batch reconstruction with one layout JSON per page.

## Install

Clone this repository into your Codex skills directory:

```bash
git clone https://github.com/KeNan-tech620/img2pptx.git ~/.codex/skills/img2pptx
```

Restart Codex after installation.

## Requirements

Use a Python environment with:

- `python-pptx`
- `Pillow`
- `numpy`

Install if needed:

```bash
python -m pip install python-pptx pillow numpy
```

## Workflow

1. Put source slide images in a working folder.
2. Classify each region as editable text, native shape, or PNG asset.
3. Run `scripts/asset_cropper.py` for complex visual assets.
4. Use `scripts/layout_from_assets.py` to scaffold image elements.
5. Add editable text, rich text runs, native shapes, and lines to the layout JSON.
6. Build the deck with `scripts/build_pptx_from_layout.py`.
7. Render a preview with `scripts/render_preview.py` when available.
8. Run `scripts/visual_diff.py` and refine the largest differences.
9. Run `scripts/inspect_pptx.py` before delivery.

## Key Commands

```bash
python scripts/font_inventory.py --check "PingFang SC" "Hiragino Sans GB" --out scratch/font_report.json
```

```bash
python scripts/asset_cropper.py \
  --manifest page_001.assets.json \
  --out-dir assets/page_001 \
  --contact-sheet
```

```bash
python scripts/layout_from_assets.py \
  --report assets/page_001/_assets_report.json \
  --source-image source.png \
  --out layouts/page_001.scaffold.layout.json
```

```bash
python scripts/build_pptx_from_layout.py \
  --layout layouts/page_001.layout.json \
  --assets-root . \
  --out output/page_001.pptx
```

```bash
python scripts/visual_diff.py \
  --source source.png \
  --preview scratch/page_001_preview.png \
  --out-dir scratch/page_001_diff
```

## Reconstruction Standard

A good reconstruction:

- Keeps ordinary text editable.
- Uses rich text runs for mixed-color editable text.
- Uses native shapes/lines for simple geometry.
- Uses PNG only for artistic text, unavailable fonts, photos, icons, generated art, and complex decoration.
- Keeps extracted assets as separate movable picture objects.
- Passes package QA and includes a visual comparison report when possible.

## License

MIT License. See [LICENSE](LICENSE).
