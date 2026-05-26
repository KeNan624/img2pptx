#!/usr/bin/env python
"""Generate alpha-crop variants for one source region.

Use this before committing a difficult crop such as neon text, glows, hairline
ornaments, or dark subjects on dark backgrounds. It writes multiple PNGs plus a
contact sheet so the best manifest parameters can be chosen by inspection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from asset_cropper import contact_sheet, load_image, render_asset, slug


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate crop parameter variants.")
    parser.add_argument("--image", required=True, help="Source image path.")
    parser.add_argument("--box", nargs=4, type=float, required=True, metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--name", default="asset", help="Base asset name.")
    parser.add_argument("--kind", choices=["luma", "mask", "transparent", "all"], default="all")
    parser.add_argument("--mask", default="orange,purple,white,bright", help="Comma-separated mask kinds.")
    parser.add_argument("--contact-sheet", action="store_true", default=True)
    return parser.parse_args()


def luma_specs(base: str, box: list[float]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for transparent, opaque, gamma in [
        (6, 46, 0.75),
        (8, 56, 0.85),
        (10, 64, 1.0),
        (14, 78, 1.0),
        (18, 92, 1.15),
        (24, 110, 1.25),
    ]:
        specs.append(
            {
                "name": f"{base}_luma_t{transparent}_o{opaque}_g{str(gamma).replace('.', '')}.png",
                "box": box,
                "mode": "luma-key",
                "transparent": transparent,
                "opaque": opaque,
                "alpha_gamma": gamma,
                "alpha_floor": 8,
                "pad": 4,
            }
        )
    return specs


def mask_specs(base: str, box: list[float], masks: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "name": f"{base}_mask_{''.join(masks)}_soft.png",
            "box": box,
            "mode": "mask",
            "mask": masks,
            "threshold": 95,
            "alpha_blur": 0.7,
            "grow": 1,
            "pad": 4,
        },
        {
            "name": f"{base}_mask_{''.join(masks)}_crisp.png",
            "box": box,
            "mode": "mask",
            "mask": masks,
            "threshold": 125,
            "pad": 4,
        },
    ]


def transparent_specs(base: str, box: list[float]) -> list[dict[str, Any]]:
    return [
        {
            "name": f"{base}_transparent_soft.png",
            "box": box,
            "mode": "transparent",
            "transparent": 5,
            "opaque": 42,
            "alpha_blur": 0.4,
            "pad": 4,
        },
        {
            "name": f"{base}_transparent_crisp.png",
            "box": box,
            "mode": "transparent",
            "transparent": 8,
            "opaque": 56,
            "pad": 4,
        },
    ]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = load_image(args.image)
    base = slug(args.name)
    box = list(args.box)
    masks = [item.strip() for item in args.mask.split(",") if item.strip()]

    specs: list[dict[str, Any]] = []
    if args.kind in {"luma", "all"}:
        specs.extend(luma_specs(base, box))
    if args.kind in {"mask", "all"}:
        specs.extend(mask_specs(base, box, masks))
    if args.kind in {"transparent", "all"}:
        specs.extend(transparent_specs(base, box))

    records: list[dict[str, Any]] = []
    files: list[Path] = []
    for spec in specs:
        rendered = render_asset(source, spec)
        path = out_dir / spec["name"]
        rendered.image.save(path)
        files.append(path)
        records.append(
            {
                "file": path.as_posix(),
                "spec": spec,
                "layout_box": rendered.layout_box,
                "size": [rendered.image.width, rendered.image.height],
            }
        )

    if args.contact_sheet:
        contact_sheet(files, out_dir / "_variants_contact_sheet.png")

    report = {
        "source": str(Path(args.image).resolve()),
        "box": box,
        "count": len(records),
        "variants": records,
    }
    report_path = out_dir / "_variants_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(records), "out_dir": str(out_dir), "report": str(report_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
