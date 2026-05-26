#!/usr/bin/env python
"""Combine per-slide layout JSON files into one multi-slide deck layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine layout JSON files.")
    parser.add_argument("--layouts", nargs="+", required=True, help="Layout files or directories.")
    parser.add_argument("--out", required=True, help="Combined layout JSON output path.")
    return parser.parse_args()


def expand_layouts(values: list[str]) -> list[Path]:
    files: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files


def slide_specs(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if doc.get("slides"):
        return list(doc["slides"])
    return [{"elements": doc.get("elements", []), "background": doc.get("background")}]


def main() -> None:
    args = parse_args()
    files = expand_layouts(args.layouts)
    if not files:
        raise SystemExit("No layout files found.")

    first = json.loads(files[0].read_text(encoding="utf-8-sig"))
    combined: dict[str, Any] = {
        "slide_size": first.get("slide_size", {"width_in": 13.333333, "height_in": 7.5}),
        "source_width": first.get("source_width") or first.get("canvas", {}).get("width") or 1182,
        "source_height": first.get("source_height") or first.get("canvas", {}).get("height") or 665,
        "background": first.get("background", "#FFFFFF"),
        "slides": [],
    }

    for file in files:
        doc = json.loads(file.read_text(encoding="utf-8-sig"))
        for slide in slide_specs(doc):
            slide = dict(slide)
            slide.setdefault("name", file.stem)
            combined["slides"].append(slide)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"slides": len(combined["slides"]), "out": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
