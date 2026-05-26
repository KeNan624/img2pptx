#!/usr/bin/env python
"""List local fonts and check whether requested font families appear installed."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FONT_DIRS = [
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local font files.")
    parser.add_argument("--check", nargs="*", default=[], help="Font family names to check.")
    parser.add_argument("--out", help="Optional JSON report path.")
    return parser.parse_args()


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def font_files() -> list[Path]:
    files: list[Path] = []
    for folder in FONT_DIRS:
        if folder.exists():
            for suffix in ("*.ttf", "*.ttc", "*.otf"):
                files.extend(folder.glob(suffix))
    return sorted(set(files), key=lambda p: p.as_posix().lower())


def main() -> None:
    files = font_files()
    records = [{"file": path.as_posix(), "stem": path.stem} for path in files]
    indexed = [(norm(path.stem), path) for path in files]
    cjk_fallbacks = [
        path.as_posix()
        for key, path in indexed
        if any(name in key for name in ("hiraginosansgb", "stheiti", "songti", "arialunicode"))
    ][:12]
    checks = []
    args = parse_args()
    for query in args.check:
        needle = norm(query)
        matches = [path.as_posix() for key, path in indexed if needle and (needle in key or key in needle)]
        wants_cjk = any(token in needle for token in ("pingfang", "microsoftyahei", "yahei", "heiti", "songti", "雅黑", "黑体", "宋体"))
        checks.append(
            {
                "query": query,
                "available": bool(matches),
                "usable_fallback_available": bool(matches) or (wants_cjk and bool(cjk_fallbacks)),
                "matches": matches[:12],
                "fallbacks": [] if matches or not wants_cjk else cjk_fallbacks,
            }
        )
    report = {"font_count": len(records), "fonts": records, "checks": checks}
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"font_count": len(records), "checks": checks}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
