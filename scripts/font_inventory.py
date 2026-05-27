#!/usr/bin/env python
"""List local fonts and check whether requested font families appear installed."""

from __future__ import annotations

import argparse
import os
import json
import re
import sys
from pathlib import Path


CJK_FONT_TOKENS = (
    "microsoftyahei",
    "msyh",
    "yahei",
    "pingfang",
    "hiragino",
    "simhei",
    "simsun",
    "stheiti",
    "songti",
    "heiti",
    "notosanscjk",
    "notosanssc",
    "notosanshans",
    "sourcehan",
    "sourcehansans",
    "arialunicode",
    "微软雅黑",
    "雅黑",
    "黑体",
    "宋体",
    "思源黑体",
)

FONT_ALIASES = {
    "microsoftyahei": ("microsoftyahei", "msyh", "yahei", "微软雅黑", "雅黑"),
    "微软雅黑": ("microsoftyahei", "msyh", "yahei", "微软雅黑", "雅黑"),
    "pingfangsc": ("pingfangsc", "pingfang", "pingfangsans", "苹方"),
    "pingfang": ("pingfangsc", "pingfang", "pingfangsans", "苹方"),
    "hiraginosansgb": ("hiraginosansgb", "hiragino", "冬青黑体"),
    "simhei": ("simhei", "黑体"),
    "黑体": ("simhei", "黑体"),
    "simsun": ("simsun", "simsunb", "宋体"),
    "宋体": ("simsun", "simsunb", "宋体"),
    "notosanscjk": ("notosanscjk", "notosanscjksc", "notosanssc", "notosanshans"),
    "sourcehansans": ("sourcehansans", "sourcehan", "思源黑体"),
    "arial": ("arial", "arialmt"),
    "arialblack": ("arialblack", "ariblk"),
    "calibri": ("calibri", "calibril", "calibrib", "calibrii", "calibriz"),
}


def default_font_dirs() -> list[Path]:
    home = Path.home()
    dirs: list[Path] = []
    if sys.platform == "darwin":
        dirs.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
                Path("/Library/Fonts"),
                home / "Library/Fonts",
            ]
        )
    elif sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local_app_data = os.environ.get("LOCALAPPDATA")
        dirs.append(windir / "Fonts")
        if local_app_data:
            dirs.append(Path(local_app_data) / "Microsoft" / "Windows" / "Fonts")
    else:
        dirs.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                home / ".fonts",
                home / ".local/share/fonts",
            ]
        )
    extra = os.environ.get("IMG2PPTX_FONT_DIRS")
    if extra:
        dirs.extend(Path(value).expanduser() for value in extra.split(os.pathsep) if value)
    return dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local font files.")
    parser.add_argument("--check", nargs="*", default=[], help="Font family names to check.")
    parser.add_argument("--out", help="Optional JSON report path.")
    parser.add_argument("--font-dir", action="append", default=[], help="Additional font directory to scan.")
    return parser.parse_args()


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def query_tokens(query: str) -> tuple[str, ...]:
    key = norm(query)
    tokens = [key]
    tokens.extend(FONT_ALIASES.get(key, ()))
    return tuple(dict.fromkeys(token for token in tokens if token))


def font_files(extra_dirs: list[str] | None = None) -> list[Path]:
    files: list[Path] = []
    folders = default_font_dirs()
    if extra_dirs:
        folders.extend(Path(value).expanduser() for value in extra_dirs)
    for folder in folders:
        if folder.exists():
            for suffix in ("*.ttf", "*.ttc", "*.otf"):
                try:
                    files.extend(folder.rglob(suffix))
                except OSError:
                    continue
    return sorted(set(files), key=lambda p: p.as_posix().lower())


def matching_paths(indexed: list[tuple[str, Path]], query: str) -> list[str]:
    needles = query_tokens(query)
    return [
        path.as_posix()
        for key, path in indexed
        if any(needle and needle in key for needle in needles)
    ]


def check_fonts(queries: list[str], extra_dirs: list[str] | None = None) -> dict[str, object]:
    files = font_files(extra_dirs)
    indexed = [(norm(path.stem), path) for path in files]
    cjk_fallbacks = [
        path.as_posix()
        for key, path in indexed
        if any(name in key for name in CJK_FONT_TOKENS)
    ][:12]
    checks = []
    for query in queries:
        matches = matching_paths(indexed, query)
        wants_cjk = any(token in CJK_FONT_TOKENS for token in query_tokens(query))
        checks.append(
            {
                "query": query,
                "available": bool(matches),
                "usable_fallback_available": bool(matches) or (wants_cjk and bool(cjk_fallbacks)),
                "matches": matches[:12],
                "fallbacks": [] if matches or not wants_cjk else cjk_fallbacks,
                "aliases": list(query_tokens(query)),
            }
        )
    return {
        "font_count": len(files),
        "fonts": [{"file": path.as_posix(), "stem": path.stem} for path in files],
        "checks": checks,
    }


def main() -> None:
    args = parse_args()
    report = check_fonts(args.check, args.font_dir)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"font_count": report["font_count"], "checks": report["checks"]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
