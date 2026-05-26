#!/usr/bin/env python
"""Render a PPTX thumbnail/preview PNG when a local renderer is available."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render PPTX preview PNG.")
    parser.add_argument("--pptx", required=True, help="Input PPTX file.")
    parser.add_argument("--out-dir", required=True, help="Preview output directory.")
    parser.add_argument("--size", type=int, default=1280, help="Preview width used by qlmanage.")
    return parser.parse_args()


def render_with_qlmanage(pptx: Path, out_dir: Path, size: int) -> Path:
    subprocess.run(
        ["qlmanage", "-t", "-s", str(size), "-o", str(out_dir), str(pptx)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    expected = out_dir / f"{pptx.name}.png"
    if expected.exists():
        return expected
    matches = sorted(out_dir.glob(f"{pptx.name}*.png"))
    if matches:
        return matches[0]
    raise RuntimeError("qlmanage completed but no PNG preview was found.")


def main() -> None:
    args = parse_args()
    pptx = Path(args.pptx)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("qlmanage"):
        preview = render_with_qlmanage(pptx, out_dir, args.size)
        print(json.dumps({"renderer": "qlmanage", "preview": str(preview)}, ensure_ascii=False, indent=2))
        return
    raise SystemExit("No supported local PPTX preview renderer found. Install LibreOffice or use macOS qlmanage.")


if __name__ == "__main__":
    main()
