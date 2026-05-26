#!/usr/bin/env python
"""Inspect a PPTX package for basic reconstruction QA."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
PLACEHOLDER_WORDS = ("Slide Number", "Click to add", "Lorem ipsum", "Replace with", "TODO", "TBD")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect PPTX package for common failures.")
    parser.add_argument("--pptx", required=True, help="PPTX path.")
    parser.add_argument("--report", help="Optional JSON report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pptx = Path(args.pptx)
    with zipfile.ZipFile(pptx) as zf:
        names = zf.namelist()
        slide_names = sorted(n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        media_names = sorted(n for n in names if n.startswith("ppt/media/"))
        texts: list[str] = []
        placeholder_text: list[dict[str, str]] = []
        for slide_name in slide_names:
            root = ET.fromstring(zf.read(slide_name))
            for node in root.findall(".//a:t", NS):
                value = node.text or ""
                if value:
                    texts.append(value)
                    if any(word in value for word in PLACEHOLDER_WORDS):
                        placeholder_text.append({"slide": slide_name, "text": value})
        zero_byte_media = [name for name in media_names if zf.getinfo(name).file_size == 0]

    failures = []
    if not slide_names:
        failures.append("PPTX contains no slides.")
    if zero_byte_media:
        failures.append("PPTX contains zero-byte media.")
    if placeholder_text:
        failures.append("PPTX contains placeholder text.")

    report = {
        "pptx": str(pptx),
        "slide_count": len(slide_names),
        "media_count": len(media_names),
        "text_run_count": len(texts),
        "text_runs": texts,
        "zero_byte_media": zero_byte_media,
        "placeholder_text": placeholder_text,
        "failures": failures,
    }
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("slide_count", "media_count", "text_run_count", "failures")}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
