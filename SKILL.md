---
name: img2pptx
description: Convert PPT slide screenshots or exported slide images into high-fidelity, maximally editable PowerPoint decks. Use when Codex needs to rebuild ordinary text as editable PPT text, preserve multi-color text with rich text runs, recreate simple geometry as native shapes, and extract only artistic typography, unsupported fonts, photos, icons, ornaments, and complex visual materials as PNG assets.
---

# PPT Image To Editable PPT

## Overview

Use this skill to turn slide images into a high-fidelity, maximally editable PowerPoint deck. The workflow is hybrid and iterative: rebuild everything that can be edited without obvious visual loss as PPT-native text/shapes, extract only unsupported artistic text and complex visuals as PNG assets, then compare the rendered PPT preview against the original image and refine the highest-error regions.

This skill is for screenshots or exported slide pages, not for editing an existing native `.pptx` file. If a source `.pptx` exists, prefer editing that deck directly.

## Required Posture

Recreate the slide, do not use a full-slide screenshot as the final slide. The default objective is: maximize visual fidelity while keeping every feasible object editable. Ordinary text must be rebuilt as editable PowerPoint text when the font and effects can be matched closely. Use rich text runs for mixed-color phrases. Use native shapes/lines for simple geometry. If a font, title treatment, glow, bevel, gradient fill, 3D effect, warped text, calligraphy, wordmark, or decorative text lockup cannot be matched with available PowerPoint features, extract that region as a transparent PNG and place it as an independent picture object. Icons, photos, line art, charts-as-images, texture, complex backgrounds, and decorative materials should also be separate PNG assets.

High-fidelity work requires the actual source image file. If the image only appears in chat and is not available on disk, do not claim high-fidelity conversion; ask for or locate the source PNG/JPG first, or clearly label the result as a low-fidelity approximation.

For Chinese academic slides, preserve institution marks and purple/gray visual systems carefully. Use the original image as the visual reference, not as a full-slide background in the final deck.

## Modes

- `max-editable-fidelity`: default. Rebuild ordinary text, colored text runs, simple shapes, and lines natively; use PNG only for artistic/unsupported/complex visual regions.
- `fidelity-first`: use when the user explicitly wants pixel closeness over editability. Extract more visual groups as PNG, but still avoid full-slide screenshots.
- `editable-first`: use only when the user explicitly prioritizes editability over visual match.

## Workflow

1. Create a workspace beside the source images:
   - `assets/page_###/` for extracted PNGs
   - `layouts/page_###.layout.json` for editable reconstruction specs
   - `output/` for final PPTX files
   - `scratch/` for previews, reports, and temporary files

2. Inspect each source image:
   - record image dimensions
   - inventory all non-text visual materials
   - classify text into editable text, rich editable text, or rasterized/artistic text assets
   - run `scripts/font_inventory.py` when font availability is uncertain
   - identify repeated templates across pages

3. Extract visual assets:
   - create an asset manifest JSON
   - run `scripts/asset_cropper.py`
   - inspect `_contact_sheet.png`
   - use `_assets_report.json` `layout_box` values when placing trimmed transparent PNGs
   - for difficult crops, run `scripts/crop_variants.py` and choose the best alpha settings
   - iterate until no obvious visual material is missing

4. Rebuild each slide:
   - create a layout JSON using source-image pixel coordinates
   - use `scripts/layout_from_assets.py` to scaffold image elements from `_assets_report.json`
   - use editable text boxes for ordinary text
   - use `runs` in text elements for mixed-color or mixed-style text
   - use native PPT shapes/lines for simple geometry
   - use extracted transparent PNGs for artistic text, unsupported fonts, icons, logos, line art, photos, charts-as-images, and complex decoration
   - build PPTX with `scripts/build_pptx_from_layout.py`

5. Batch and merge:
   - build representative pages first
   - for a deck, create one layout JSON per page
   - combine layouts with `scripts/combine_layouts.py`
   - export one final PPTX

6. QA:
   - run `scripts/inspect_pptx.py`
   - render or preview the saved PPTX when available
   - run `scripts/visual_diff.py` against the source image and preview PNG
   - compare the preview against the source images
   - fix the largest visual-diff regions first
   - report output PPTX path, asset folder path, preview/report paths, and unresolved fidelity differences

## Read These References As Needed

- `references/asset-manifest.md`: asset crop manifest format and extraction modes.
- `references/layout-json.md`: editable PPT layout JSON schema.
- `references/reconstruction-sop.md`: full per-slide and batch checklist.
- `references/fidelity-workflow.md`: high-fidelity iteration workflow, modes, and QA thresholds.
- `references/editability-decisions.md`: rules for choosing PPT-native text/shape vs PNG assets.

Read `editability-decisions.md` before deciding to crop any text as PNG. Read `asset-manifest.md` before writing crop manifests. Read `layout-json.md` before writing layout JSON. Read `reconstruction-sop.md` for batch jobs or when the slide is visually dense. Read `fidelity-workflow.md` for visually rich slides or whenever the user asks for maximum source-image fidelity.

## Script Commands

Use the active Python environment. If `python-pptx` is missing, install it into that environment:

```bash
python -m pip install python-pptx
```

For image work, Pillow and NumPy are required. The Codex bundled workspace Python usually includes them.

Check local font availability:

```bash
python /path/to/skill/scripts/font_inventory.py \
  --check "PingFang SC" "Microsoft YaHei" "Arial Black" \
  --out scratch/font_report.json
```

Extract assets:

```bash
python /path/to/skill/scripts/asset_cropper.py \
  --manifest page_002.assets.json \
  --out-dir assets/page_002 \
  --contact-sheet
```

Generate crop variants for a difficult region:

```bash
python /path/to/skill/scripts/crop_variants.py \
  --image source.png \
  --box 48 88 512 318 \
  --name hero_title \
  --out-dir scratch/hero_title_variants
```

Scaffold layout image elements from crop reports:

```bash
python /path/to/skill/scripts/layout_from_assets.py \
  --report assets/page_001/_assets_report.json \
  --source-image source.png \
  --out layouts/page_001.scaffold.layout.json
```

Build one or more slides from layout JSON:

```bash
python /path/to/skill/scripts/build_pptx_from_layout.py \
  --layout layouts/page_002.layout.json \
  --assets-root . \
  --out output/page_002_editable.pptx
```

Combine per-page layouts:

```bash
python /path/to/skill/scripts/combine_layouts.py \
  --layouts layouts \
  --out layouts/combined.layout.json
```

Inspect final PPTX:

```bash
python /path/to/skill/scripts/inspect_pptx.py \
  --pptx output/deck_editable.pptx \
  --report scratch/quality_report.json
```

Render a local preview PNG when a renderer is available:

```bash
python /path/to/skill/scripts/render_preview.py \
  --pptx output/deck_editable.pptx \
  --out-dir scratch
```

Compare a rendered preview against the source:

```bash
python /path/to/skill/scripts/visual_diff.py \
  --source source.png \
  --preview scratch/page_001_preview.png \
  --out-dir scratch/page_001_diff
```

## Extraction Decisions

Extract separately:

- logos, emblems, seals, wordmarks
- artistic typography, hero titles, unsupported fonts, gradient/glow/bevel/3D text, and decorative text lockups
- icons and pictograms
- photos, screenshots, chart screenshots when not reconstructing as data
- background campus/architecture line art
- footer/header decorative bands
- complex ribbons, tabs, badge shapes, paired flourishes
- reusable blank variants such as blank circles or empty ribbon tabs when useful

Do not extract:

- normal body text that can be matched with installed fonts
- mixed-color plain text that can be represented with `runs`
- plain titles, section labels, captions, bullets, and numbers that can be rebuilt accurately as text
- simple rectangles, card frames, circles, and straight rules that can be native PPT shapes

Do not approximate distinctive source art with a generic PowerPoint font. If the result would visibly differ, extract that text or visual group as PNG. But do not crop ordinary labels, captions, subtitles, nav text, or footer text just to improve pixel metrics; keep them editable unless the user explicitly asks for pixel-perfect raster fidelity.

## Reconstruction Decisions

Use source-image pixel coordinates in layout JSON. Set `source_width` and `source_height` to the image size. The builder scales positions to the requested slide size.

Element order matters. Place backgrounds first, then large shapes, then image assets, then text.

When using `asset_cropper.py`, prefer the `layout_box` emitted in `_assets_report.json` for image elements. The cropper may trim transparent edges, and the reported `layout_box` preserves the correct source-image position.

Keep text boxes generous. PowerPoint, WPS, and preview renderers can use slightly different font metrics. Prefer wider boxes, explicit line breaks, and modest font-size adjustments over tight text regions.

Use dual-layer text only for borderline cases: visible PNG for exact artistic appearance plus a matching editable text layer behind it or in a reference area. Do not use dual-layer text for ordinary copy that can be rendered visibly as editable text.

For repeated page templates, create a reusable layout pattern and only swap text/image paths per page. For highly varied pages, rebuild each page individually.

## Validation Standard

A job is done only when:

- every meaningful visual asset from the source slide is either extracted as a PNG or intentionally rebuilt as a native shape
- ordinary matched text is editable in the PPTX; artistic or unsupported text is preserved as transparent PNG assets
- PNG assets are independent picture objects and can be moved/replaced
- final PPTX passes package inspection with no empty media or placeholder text
- the saved PPTX preview has been visually compared against the source image, preferably with `visual_diff.py`, or the final response states why preview parity could not be rendered

Final responses should include the final `.pptx` path, extracted asset root, preview path if generated, package QA report, visual diff report when available, and any known differences from the source image.
