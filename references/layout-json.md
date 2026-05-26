# Layout JSON Reference

Use layout JSON when rebuilding slide images as editable PPTX files with `scripts/build_pptx_from_layout.py`.

## Top Level

```json
{
  "slide_size": { "width_in": 13.333333, "height_in": 7.5 },
  "source_width": 1182,
  "source_height": 665,
  "background": "#FFFFFF",
  "slides": [
    {
      "background": "#FFFFFF",
      "elements": []
    }
  ]
}
```

Coordinates are in source-image pixels. The script scales them to the PowerPoint slide size.

For a one-slide layout, `elements` may be placed at the top level instead of under `slides`.

## Elements

### Text

```json
{
  "type": "text",
  "name": "slide-title",
  "text": "目  录",
  "box": [532, 138, 122, 58],
  "font": "KaiTi",
  "size": 31,
  "bold": true,
  "color": "#481258",
  "align": "center",
  "valign": "middle",
  "line_spacing": 1.05
}
```

Use editable text for all normal slide copy. Preserve line breaks from the reference image when they are part of layout.

Use `runs` when a text box contains mixed colors or styles while still being ordinary editable text:

```json
{
  "type": "text",
  "name": "subtitle",
  "box": [84, 336, 340, 31],
  "font": "PingFang SC",
  "size": 21,
  "bold": true,
  "color": "#F6F6F8",
  "align": "left",
  "valign": "middle",
  "runs": [
    { "text": "读懂人工智能的" },
    { "text": "现在", "color": "#FF861F" },
    { "text": "与" },
    { "text": "未来", "color": "#A15CFF" }
  ]
}
```

Each run inherits the parent text style unless it overrides `font`, `size`, `bold`, `italic`, or `color`.

### Image

```json
{
  "type": "image",
  "name": "icon-document",
  "path": "assets/page_002/18_icon_document.png",
  "box": [112, 332, 51, 59]
}
```

Use images for extracted logos, icons, background ornaments, line art, photos, and complex decorative marks.

For assets produced by `scripts/asset_cropper.py`, prefer the image element emitted in `_assets_report.json` as `layout_element`. It uses the post-trim `layout_box`, which prevents transparent PNGs from being stretched or shifted after alpha trimming.

To scaffold a layout directly from crop reports:

```bash
python scripts/layout_from_assets.py \
  --report assets/page_001/_assets_report.json \
  --source-image source.png \
  --out layouts/page_001.scaffold.layout.json
```

Then add editable text, native lines, and simple shapes to the scaffold.

### Shape

```json
{
  "type": "shape",
  "name": "catalog-card-01",
  "shape": "rounded_rect",
  "box": [64, 225, 146, 306],
  "fill": "transparent",
  "line": "#BCB9BE",
  "line_width": 1,
  "radius": 0.06
}
```

Supported shapes include `rect`, `rounded_rect`, `oval`, `diamond`, `triangle`, and `trapezoid`.

### Line

```json
{
  "type": "line",
  "name": "divider",
  "points": [861, 329, 1104, 329],
  "line": "#D6D6D6",
  "line_width": 0.7,
  "dash": "dash"
}
```

Use native lines for separators and rules when they are simple. Use extracted images for complex gradient/ornamental lines.

## Ordering

Elements render in list order. Put background bands and large decorative images first, then frames/shapes, then icons, then text.

## Batch Layouts

For many pages, create one `page_###.layout.json` per source image. Combine them with:

```bash
python scripts/combine_layouts.py --layouts layouts --out combined.layout.json
python scripts/build_pptx_from_layout.py --layout combined.layout.json --assets-root . --out output/deck.pptx
```
