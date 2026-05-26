# Editability Decisions

Use this before converting text or simple shapes into PNG assets. The target is maximum visual fidelity subject to maximum editability.

## Default Decision Order

1. Native PPT text if the content is ordinary text and a close font is available.
2. Native rich text runs if one text line contains multiple colors, weights, or sizes.
3. Native shapes/lines for simple frames, circles, separators, rules, cards, arrows, and basic icons.
4. PNG asset for artistic typography, unavailable fonts, wordmarks, photos, screenshots, generated art, glows, textures, complex icons, and detailed ornaments.
5. Dual-layer text only when text must look exact but should remain searchable/copyable.

## Text Rules

Keep as editable text:

- body text, subtitles, captions, bullets, labels, footers, dates, numbers
- navigation labels such as "现状 / 机遇 / 挑战 / 未来"
- plain headers such as "人工智能主题汇报" when the font is available or close
- mixed-color plain phrases, using `runs`

Use PNG for text:

- large artistic titles with gradient fill, bevel, glow, perspective, or heavy shadow
- calligraphy, logos, seals, decorative wordmarks
- text using a font unavailable in the PPT editing environment when substitution is visibly wrong
- text fused with complex background art where separation would damage the look

## Font Check

Run `font_inventory.py` when unsure:

```bash
python scripts/font_inventory.py --check "PingFang SC" "Microsoft YaHei" "Arial Black" --out scratch/font_report.json
```

If no close font exists and visual match matters, crop the text as PNG. If a close font exists, rebuild it as text and use visual diff only to tune size, box, alignment, and line spacing.

## Rich Text Runs

Use `runs` for text like:

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
    { "text": "读懂人工智能的", "color": "#F6F6F8" },
    { "text": "现在", "color": "#FF861F" },
    { "text": "与", "color": "#F6F6F8" },
    { "text": "未来", "color": "#A15CFF" }
  ]
}
```

## Visual Diff Tradeoff

Do not optimize SSIM by rasterizing ordinary editable text unless the user explicitly asks for pixel-perfect reproduction. For normal conversion jobs, report that residual diff comes from editable text rendering and preserve editability.
