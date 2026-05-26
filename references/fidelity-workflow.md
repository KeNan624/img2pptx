# High-Fidelity Reconstruction Workflow

Use this reference when the user asks for maximum visual fidelity, when the slide contains artistic typography, or when a first pass looks visibly different from the source image.

## Modes

`max-editable-fidelity` is the default. Extract artistic text, complex backgrounds, photos, generated art, icons, chart screenshots, glow effects, and detailed ornaments as PNG assets. Rebuild plain text, rich text runs, simple shapes, and lines as native PowerPoint objects.

`fidelity-first` is for explicit pixel-closeness requests. It may extract larger visual groups as PNG, but should still avoid full-slide screenshots.

`balanced` is for business decks where text editability matters and visual styling is moderate.

`editable-first` is only for requests that explicitly prioritize editability over visual match.

## Required Source Rule

Do not promise high-fidelity output without an actual source PNG/JPG/PDF-exported slide image on disk. If the source is only visible in chat or a screenshot thumbnail, first ask for the source file or state that the output is an approximation.

## Iteration Loop

1. Create a crop manifest with all visually meaningful regions.
2. Run `asset_cropper.py --contact-sheet`.
3. Classify each text region using `editability-decisions.md`.
4. For difficult PNG regions, run `crop_variants.py` and choose the best variant.
5. Build a layout scaffold with `layout_from_assets.py`.
6. Add editable text, rich text runs, and simple native shapes.
7. Build the PPTX.
8. Render or preview the PPTX as PNG with `render_preview.py` when possible.
9. Run `visual_diff.py`.
10. Refine the highest-error regions without rasterizing ordinary text unless requested.

## Crop Strategy

Prefer larger visual groups when separability is not needed. For example, a hero title with glow and shadows should usually be one PNG, not separate text boxes.

Split only when the user likely needs to move or replace pieces independently, such as a logo, four navigation icons, a photo, or a reusable decorative badge.

For dark slides with neon text, start with `luma-key`. If glow edges are weak, lower `transparent`, lower `opaque`, use `alpha_gamma` below 1, or add `alpha_floor`.

For colored icons, use `mask` with multiple color families. Add `grow: 1` and `alpha_blur: 0.5` when thin strokes break.

For exact photo or generated-art regions, use `keep` and crop the full rectangular region.

## Visual QA

Use `visual_diff.py` after rendering the deck preview. Interpret metrics as directional, not absolute:

- `ssim >= 0.94`: good for a mixed editable/raster reconstruction.
- `ssim 0.88-0.94`: inspect the top error regions and refine.
- `ssim < 0.88`: likely missing or mispositioned large assets.

Fix errors in this order:

1. Missing or shifted large PNG assets.
2. Wrong z-order.
3. Over-aggressive alpha trimming.
4. Text incorrectly rasterized when it should be editable.
5. Artistic text rendered natively when it should be a PNG.
6. Font size, line spacing, and alignment differences in editable text.

## Dual-Layer Text

When text must look exactly like the source but remain available for editing/search, use a transparent PNG as the visible layer and add a matching editable text box behind it or in a reference area. The visible PNG preserves fidelity; the hidden/native text preserves semantic access.
