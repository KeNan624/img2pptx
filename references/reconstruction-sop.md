# Reconstruction SOP

Use this checklist for each source slide image.

## 1. Inspect

Record:

- source image size
- slide aspect ratio and target PPT size
- dominant colors
- visual asset inventory: logos, icons, photos, background ornaments, rules, cards, ribbons, separators, badges
- text inventory split into:
  - editable text: ordinary labels, captions, body copy, numbers, and headings that can be matched with installed fonts
  - rich editable text: ordinary text with mixed colors or weights that can be built with `runs`
  - rasterized text assets: artistic typography, unsupported fonts, warped/outlined/gradient/glow/bevel/3D text, wordmarks, and decorative title lockups

For repeated page templates, solve one representative slide first, then reuse its geometry and adjust only page-specific content.

## 2. Extract Assets

Create `page_###.assets.json`.

Extract:

- logos and wordmarks
- artistic or unsupported typography that cannot be recreated accurately with PPT fonts
- icons and pictograms
- photos/screenshots
- background line art and decorative bands
- complex ribbons, flourishes, badges, patterned rules
- reusable blank variants when useful, such as blank numbered circles or empty tabs

Do not extract normal editable slide text as PNG. Rebuild it as PowerPoint text boxes, using `runs` for mixed-color phrases. Do extract text when PowerPoint font substitution would visibly degrade the source image.

Run `asset_cropper.py`, inspect `_contact_sheet.png`, and iterate until no obvious asset is missing or damaged. Also open `_assets_report.json`; use the emitted `layout_box` or `layout_element` for each PNG because transparent trimming changes the placement box.

For difficult crops, run `crop_variants.py` and pick the best settings from `_variants_contact_sheet.png` before finalizing the manifest.

## 3. Rebuild As Editable PPT

Create `page_###.layout.json`.

Start with `layout_from_assets.py` when most visual elements are PNG assets. It converts `_assets_report.json` into image elements with correct source-coordinate boxes.

Prefer native PowerPoint objects:

- text boxes for all ordinary text
- rich text runs for mixed-color ordinary text
- shapes for card frames, circles, simple rectangles, and basic separators
- lines/connectors for simple rules and dividers
- images for extracted assets, including artistic text and complex visual groups

Use source-image pixel coordinates in layout JSON. Preserve element ordering from background to foreground.

Keep each text box roomy. If rendered text wraps differently from the source, adjust box width/height, font, or line breaks instead of shrinking to unreadable sizes.

Do not spend time hand-recreating complex art in PPT primitives when a transparent PNG crop will match the source better. The target is a deck where ordinary text remains editable and source-specific visual treatments remain visually faithful.

## 4. Batch

For many pages:

1. Create one asset folder per page: `assets/page_001`, `assets/page_002`, ...
2. Create one layout file per page: `layouts/page_001.layout.json`, ...
3. Build and preview a few representative pages first.
4. Combine all layouts with `combine_layouts.py`.
5. Build the final deck with `build_pptx_from_layout.py`.

## 5. QA

Run `inspect_pptx.py` on the final PPTX.

Also render or open a preview of the saved PPTX when available. Compare to the source images and check:

- no missing icons or decorative materials
- ordinary text remains editable, while artistic/unsupported text is preserved as movable PNG assets
- images remain editable picture objects
- frames, ribbons, footer/header bands, and major alignments match the source
- no text clipping or accidental wrapping
- no placeholder text or empty media

When a rendered preview PNG is available, run `visual_diff.py` and refine the largest mismatch regions first.

If a preview renderer is unavailable, still inspect the PPTX package and state that visual parity was checked by opening/exporting through the available tool or by manual image comparison.
