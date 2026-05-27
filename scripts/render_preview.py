#!/usr/bin/env python
"""Render a PPTX thumbnail/preview PNG when a local renderer is available."""

from __future__ import annotations

import argparse
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render PPTX preview PNG.")
    parser.add_argument("--pptx", required=True, help="Input PPTX file.")
    parser.add_argument("--out-dir", required=True, help="Preview output directory.")
    parser.add_argument("--size", type=int, default=1280, help="Preview width in pixels when supported.")
    return parser.parse_args()


def find_libreoffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    candidates: list[Path] = []
    if sys.platform == "darwin":
        candidates.append(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"))
    elif sys.platform == "win32":
        for root in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            value = os.environ.get(root)
            if value is None:
                for key, env_value in os.environ.items():
                    if key.upper() == root:
                        value = env_value
                        break
            if value:
                candidates.append(Path(value) / "LibreOffice" / "program" / "soffice.exe")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def windows_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is not None:
        return value
    for key, env_value in os.environ.items():
        if key.upper() == name.upper():
            return env_value
    return None


def windows_app_path(name: str) -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ModuleNotFoundError:
        return None
    keys = (
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{name}"),
    )
    for root, subkey in keys:
        try:
            with winreg.OpenKey(root, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "")
        except OSError:
            continue
        if value and Path(value).exists():
            return value
    return None


def find_powerpoint() -> str | None:
    if sys.platform != "win32":
        return None
    for name in ("POWERPNT.EXE", "powerpnt.exe"):
        path = shutil.which(name)
        if path:
            return path
    registry_path = windows_app_path("POWERPNT.EXE")
    if registry_path:
        return registry_path
    candidates: list[Path] = []
    for root_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = windows_env(root_name)
        if not root:
            continue
        base = Path(root) / "Microsoft Office"
        candidates.append(base / "root" / "Office16" / "POWERPNT.EXE")
        for version in ("Office16", "Office15", "Office14", "Office12"):
            candidates.append(base / version / "POWERPNT.EXE")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


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


def render_with_powerpoint(pptx: Path, out_dir: Path, size: int) -> Path:
    if sys.platform != "win32":
        raise RuntimeError("PowerPoint COM rendering is only available on Windows.")
    try:
        import pythoncom  # type: ignore[import-not-found]
        import win32com.client  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install pywin32 to render previews with Microsoft PowerPoint: python -m pip install pywin32") from exc

    pythoncom.CoInitialize()
    app = None
    presentation = None
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        app.Visible = 1
        presentation = app.Presentations.Open(str(pptx.resolve()), WithWindow=False)
        slide = presentation.Slides(1)
        slide_width = float(presentation.PageSetup.SlideWidth)
        slide_height = float(presentation.PageSetup.SlideHeight)
        width = int(size)
        height = max(1, int(round(width * slide_height / slide_width)))
        out_path = out_dir / f"{pptx.stem}_powerpoint_preview.png"
        slide.Export(str(out_path.resolve()), "PNG", width, height)
        if out_path.exists():
            return out_path
        raise RuntimeError("PowerPoint completed but no PNG preview was found.")
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()


def run_libreoffice_convert(executable: str, pptx: Path, out_dir: Path, target: str) -> None:
    subprocess.run(
        [executable, "--headless", "--convert-to", target, "--outdir", str(out_dir), str(pptx)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def render_pdf_with_pymupdf(pdf: Path, out_path: Path, size: int) -> Path | None:
    try:
        import fitz  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return None
    doc = fitz.open(pdf)
    try:
        page = doc[0]
        zoom = size / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pix.save(out_path)
        return out_path
    finally:
        doc.close()


def render_pdf_with_pdftoppm(pdf: Path, out_path: Path, size: int) -> Path | None:
    executable = shutil.which("pdftoppm")
    if not executable:
        return None
    prefix = out_path.with_suffix("")
    subprocess.run(
        [executable, "-png", "-singlefile", "-scale-to-x", str(size), "-scale-to-y", "-1", str(pdf), str(prefix)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    expected = prefix.with_suffix(".png")
    if expected.exists() and expected != out_path:
        expected.replace(out_path)
    return out_path if out_path.exists() else None


def render_pdf_with_magick(pdf: Path, out_path: Path, size: int) -> Path | None:
    executable = shutil.which("magick")
    if not executable:
        return None
    subprocess.run(
        [executable, "-density", "144", f"{pdf}[0]", "-resize", f"{size}x", str(out_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return out_path if out_path.exists() else None


def render_with_libreoffice(pptx: Path, out_dir: Path, size: int) -> Path:
    executable = find_libreoffice()
    if not executable:
        raise RuntimeError("LibreOffice executable was not found.")

    before = {path.resolve() for path in out_dir.glob("*.png")}
    try:
        run_libreoffice_convert(executable, pptx, out_dir, "png")
    except subprocess.CalledProcessError:
        pass
    matches = sorted(
        path
        for path in out_dir.glob("*.png")
        if path.resolve() not in before and path.stem.startswith(pptx.stem)
    )
    if matches:
        return matches[0]

    run_libreoffice_convert(executable, pptx, out_dir, "pdf")
    pdf = out_dir / f"{pptx.stem}.pdf"
    if not pdf.exists():
        matches = sorted(out_dir.glob(f"{pptx.stem}*.pdf"))
        if matches:
            pdf = matches[0]
    if not pdf.exists():
        raise RuntimeError("LibreOffice completed but no PDF preview source was found.")

    out_path = out_dir / f"{pptx.stem}_preview.png"
    for renderer in (
        render_pdf_with_pymupdf,
        render_pdf_with_pdftoppm,
        render_pdf_with_magick,
    ):
        preview = renderer(pdf, out_path, size)
        if preview:
            return preview
    raise RuntimeError("LibreOffice exported PDF, but no PDF-to-PNG renderer was found.")


def main() -> None:
    args = parse_args()
    pptx = Path(args.pptx)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    if shutil.which("qlmanage"):
        preview = render_with_qlmanage(pptx, out_dir, args.size)
        print(json.dumps({"renderer": "qlmanage", "preview": str(preview)}, ensure_ascii=False, indent=2))
        return
    if find_powerpoint():
        try:
            preview = render_with_powerpoint(pptx, out_dir, args.size)
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            print(json.dumps({"renderer": "powerpoint", "preview": str(preview)}, ensure_ascii=False, indent=2))
            return
    if find_libreoffice():
        try:
            preview = render_with_libreoffice(pptx, out_dir, args.size)
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            print(json.dumps({"renderer": "libreoffice", "preview": str(preview)}, ensure_ascii=False, indent=2))
            return
    message = "No supported local PPTX preview renderer found. Install Microsoft PowerPoint plus pywin32 on Windows, LibreOffice, or use macOS qlmanage."
    if errors:
        message += " Errors: " + " | ".join(errors)
    raise SystemExit(message)


if __name__ == "__main__":
    main()
