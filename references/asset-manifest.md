# Asset Manifest Reference

Use an asset manifest to drive `scripts/asset_cropper.py`. The agent decides the crop boxes by inspecting the source slide image.

## Single Image Manifest

```json
{
  "source": "slide_02.png",
  "assets": [
    {
      "name": "01_header_logo_full.png",
      "box": [48, 36, 254, 101],
      "mode": "transparent",
      "transparent": 5,
      "opaque": 38,
      "pad": 3
    },
    {
      "name": "02_hero_art_title.png",
      "box": [54, 95, 507, 314],
      "mode": "luma-key",
      "transparent": 22,
      "opaque": 86,
      "pad": 6
    },
    {
      "name": "10_research_ribbon_blank.png",
      "box": [870, 178, 1083, 234],
      "mode": "mask",
      "mask": "purple",
      "row_fill_holes": true,
      "blank": true,
      "pad": 2
    }
  ]
}
```

Run:

```bash
python scripts/asset_cropper.py --manifest page_002.assets.json --out-dir assets/page_002 --contact-sheet
```

The cropper writes `_assets_report.json`. For each asset, copy `layout_element` or at least its `layout_box` into the layout JSON. This matters when transparent edges are trimmed; using the original crop box can stretch or misplace the PNG.

## Batch Manifest

```json
{
  "images": [
    {
      "source": "slide_01.png",
      "out_dir": "page_001",
      "assets": []
    },
    {
      "source": "slide_02.png",
      "out_dir": "page_002",
      "assets": []
    }
  ]
}
```

Run:

```bash
python scripts/asset_cropper.py --manifest batch.assets.json --out-dir assets --contact-sheet
```

## Asset Modes

`transparent`: remove a flat background sampled from crop corners. Best for icons, logos, purple line art on white background, and decorations.

`keep`: crop exactly and preserve all pixels. Best for full-width footer bars, photo areas, screenshots, or textured backgrounds.

`luma-key`: make dark background transparent while preserving bright or saturated pixels. Best for neon, gradient, glow, bevel, and large artistic title text on dark slides. Tune `transparent` and `opaque`; lower values keep more glow.

`mask`: keep pixels matching a color family and make everything else transparent. Use `mask: "purple"` for purple ribbons or icons, `mask: "orange"` for orange accents, `mask: "white"` for white glyphs, `mask: "bright"` for any bright region, `mask: "dark"` for dark marks, or `mask: "non-bg"` for anything different from a specified/sampled background. `mask` may also be a list, such as `["orange", "white", "purple"]`. Use `feather` to soften mask edges.

`ellipse` or `circle`: create an oval/circular alpha mask for circular badges or numbered dots. Use `blank: true` and `fill` to create reusable blank circles without text.

## Alpha Controls

Use these optional fields with `luma-key`, `mask`, or `transparent` when edges need refinement:

- `alpha_floor`: minimum alpha for any retained pixel; useful for preserving faint glow.
- `alpha_gamma`: adjusts alpha curve. Values below 1 preserve soft edges; values above 1 make edges crisper.
- `alpha_blur` or `feather`: softens alpha edges.
- `grow` / `dilate`: expands the alpha mask to preserve thin strokes.
- `shrink` / `erode`: contracts the alpha mask to remove halos.

For difficult regions, run:

```bash
python scripts/crop_variants.py --image source.png --box 48 88 512 318 --name hero_title --out-dir scratch/hero_title_variants
```

Then inspect `_variants_contact_sheet.png` and copy the best variant's `spec` from `_variants_report.json` back into the crop manifest.

## Extraction Rules

Extract image/icon materials, not normal body text. Treat wordmarks, logos, seals, stylized calligraphy, artistic headlines, unavailable fonts, gradient/glow/bevel/3D text, and emblems as visual assets when they would be hard to recreate as editable text.

For a visually distinctive headline, do not approximate it with a generic PPT font. Crop it as one transparent PNG if it behaves as one visual lockup, or split it into separate PNGs when pieces need independent movement.

Make one PNG per reusable visual asset. Merge tiny decorative fragments only when they are visually inseparable or only useful as a group, such as a footer ornament strip or paired title flourish.

Always generate `_contact_sheet.png` and inspect it. If a white glyph inside a purple circle disappears, rerun that asset with `mode: "ellipse"` or `mode: "mask"` instead of corner-background removal.

Always inspect `_assets_report.json` before writing layout image elements. Prefer each asset's reported `layout_element` because it already accounts for alpha trimming.
