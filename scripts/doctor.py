#!/usr/bin/env python
"""Check whether the local environment can run the img2pptx workflow."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from font_inventory import check_fonts
from render_preview import find_libreoffice, find_powerpoint


DEFAULT_FONT_CHECKS = [
    "Microsoft YaHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "SimHei",
    "SimSun",
    "Noto Sans CJK",
    "Arial",
    "Arial Black",
    "Calibri",
]

DEPENDENCIES = [
    ("python-pptx", "pptx"),
    ("Pillow", "PIL"),
    ("numpy", "numpy"),
]

OPTIONAL_DEPENDENCIES = [
    ("PyMuPDF", "fitz"),
]

WINDOWS_OPTIONAL_DEPENDENCIES = [
    ("pywin32", "win32com.client"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check img2pptx environment readiness.")
    parser.add_argument("--out", help="Optional JSON report path.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report instead of a short summary.")
    parser.add_argument("--check-font", action="append", default=[], help="Additional font family to check.")
    parser.add_argument("--font-dir", action="append", default=[], help="Additional font directory to scan.")
    return parser.parse_args()


def package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_dependency(package: str, module: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "package": package,
        "module": module,
        "available": False,
        "version": package_version(package),
        "path": None,
    }
    try:
        imported = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - diagnostics should report import failures verbatim.
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["available"] = True
    record["path"] = getattr(imported, "__file__", None)
    if record["version"] is None:
        record["version"] = getattr(imported, "__version__", None)
    return record


def executable_record(name: str, path: str | None = None) -> dict[str, Any]:
    found = path or shutil.which(name)
    return {"name": name, "available": bool(found), "path": found}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    libreoffice = find_libreoffice()
    powerpoint = find_powerpoint()
    dependencies = [check_dependency(package, module) for package, module in DEPENDENCIES]
    optional_dependency_specs = list(OPTIONAL_DEPENDENCIES)
    if sys.platform == "win32":
        optional_dependency_specs.extend(WINDOWS_OPTIONAL_DEPENDENCIES)
    optional_dependencies = [check_dependency(package, module) for package, module in optional_dependency_specs]
    fonts = check_fonts(DEFAULT_FONT_CHECKS + args.check_font, args.font_dir)
    font_summary = {"font_count": fonts["font_count"], "checks": fonts["checks"]}
    executables = [
        executable_record("qlmanage"),
        executable_record("powerpoint", powerpoint),
        executable_record("libreoffice", libreoffice),
        executable_record("soffice", shutil.which("soffice")),
        executable_record("pdftoppm"),
        executable_record("magick"),
    ]

    recommendations: list[str] = []
    missing_required = [item["package"] for item in dependencies if not item["available"]]
    if missing_required:
        recommendations.append("Install required Python packages: python -m pip install python-pptx pillow numpy")
    pywin32_available = any(item["package"] == "pywin32" and item["available"] for item in optional_dependencies)
    powerpoint_preview_available = bool(powerpoint) and pywin32_available
    if sys.platform == "win32" and powerpoint and not pywin32_available:
        recommendations.append("Install pywin32 to render previews with local Windows PowerPoint: python -m pip install pywin32")
    if not any(item["available"] and item["name"] in {"qlmanage", "libreoffice", "soffice"} for item in executables) and not powerpoint_preview_available:
        recommendations.append("Install Microsoft PowerPoint plus pywin32, LibreOffice, or run on macOS with qlmanage for local PPTX preview rendering.")
    pymupdf_available = any(item["package"] == "PyMuPDF" and item["available"] for item in optional_dependencies)
    if libreoffice and not pymupdf_available and not shutil.which("pdftoppm") and not shutil.which("magick"):
        recommendations.append("Install PyMuPDF, Poppler pdftoppm, or ImageMagick if LibreOffice only exports PDF previews.")
    weak_fonts = [
        item["query"]
        for item in font_summary["checks"]
        if item["query"] in {"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "SimHei", "SimSun", "Noto Sans CJK"}
        and not item["usable_fallback_available"]
    ]
    if weak_fonts:
        recommendations.append("Install or bundle the fonts used by the source slides, especially Chinese UI/body fonts.")

    ready = not missing_required
    return {
        "ready": ready,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "dependencies": dependencies,
        "optional_dependencies": optional_dependencies,
        "executables": executables,
        "fonts": font_summary,
        "recommendations": recommendations,
    }


def print_summary(report: dict[str, Any]) -> None:
    print(f"img2pptx environment: {'ready' if report['ready'] else 'needs attention'}")
    print(f"platform: {report['platform']['system']} {report['platform']['release']} ({report['platform']['machine']})")
    print(f"python: {report['python']['version']} at {report['python']['executable']}")
    print("")
    print("required packages:")
    for item in report["dependencies"]:
        status = "ok" if item["available"] else "missing"
        version = f" {item['version']}" if item.get("version") else ""
        print(f"  - {item['package']}: {status}{version}")
    print("")
    print("preview tools:")
    for item in report["executables"]:
        status = "ok" if item["available"] else "missing"
        path = f" ({item['path']})" if item.get("path") else ""
        print(f"  - {item['name']}: {status}{path}")
    print("")
    print(f"fonts scanned: {report['fonts']['font_count']}")
    for item in report["fonts"]["checks"]:
        status = "ok" if item["available"] else "fallback" if item["usable_fallback_available"] else "missing"
        print(f"  - {item['query']}: {status}")
    if report["recommendations"]:
        print("")
        print("recommendations:")
        for item in report["recommendations"]:
            print(f"  - {item}")


def main() -> None:
    args = parse_args()
    report = build_report(args)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_summary(report)


if __name__ == "__main__":
    main()
