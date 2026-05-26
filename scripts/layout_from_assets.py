#!/usr/bin/env python
"""Create a layout JSON scaffold from asset_cropper reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a layout scaffold from _assets_report.json.")
    parser.add_argument("--report", nargs="+", required=True, help="One or more asset report JSON files.")
    parser.add_argument("--out", required=True, help="Output layout JSON.")
    parser.add_argument("--source-image", help="Source image used for source_width/source_height.")
    parser.add_argument("--background", default="#020204", help="Slide background color.")
    parser.add_argument("--slide-width-in", type=float, default=13.333333)
    parser.add_argument("--slide-height-in", type=float, default=7.5)
    parser.add_argument("--texts", help="Optional JSON file with text/shape/line elements to append.")
    parser.add_argument("--name", default="reconstructed-slide")
    return parser.parse_args()


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def source_size(args: argparse.Namespace, reports: list[dict[str, Any]]) -> tuple[int, int]:
    if args.source_image:
        img = Image.open(args.source_image)
        return img.width, img.height
    for report in reports:
        for asset in report.get("assets", []):
            source = asset.get("source")
            if source and Path(source).exists():
                img = Image.open(source)
                return img.width, img.height
    return 960, 540


def normalize_path(path_value: str, out_path: Path) -> str:
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(out_path.parent).as_posix()
    except ValueError:
        return path.as_posix()


def elements_from_report(report: dict[str, Any], out_path: Path) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for asset in report.get("assets", []):
        el = dict(asset.get("layout_element") or {})
        if not el:
            el = {
                "type": "image",
                "name": asset.get("name") or Path(asset["file"]).stem,
                "path": asset["file"],
                "box": asset["layout_box"],
            }
        el["path"] = normalize_path(el["path"], out_path)
        elements.append(el)
    return elements


def extra_elements(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    doc = read_json(path)
    if isinstance(doc, list):
        return doc
    return list(doc.get("elements", []))


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    reports = [read_json(path) for path in args.report]
    width, height = source_size(args, reports)
    elements: list[dict[str, Any]] = []
    for report in reports:
        elements.extend(elements_from_report(report, out))
    elements.extend(extra_elements(args.texts))

    layout = {
        "slide_size": {"width_in": args.slide_width_in, "height_in": args.slide_height_in},
        "source_width": width,
        "source_height": height,
        "background": args.background,
        "slides": [{"name": args.name, "background": args.background, "elements": elements}],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "elements": len(elements), "source_size": [width, height]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
