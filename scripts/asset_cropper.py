#!/usr/bin/env python
"""Crop slide-image assets to PNG files from a manifest.

The agent still decides what should be extracted. This script makes the crop,
background removal, alpha trimming, and contact sheet generation repeatable.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class RenderedAsset:
    image: Image.Image
    crop_box: list[int]
    trim_box: list[int]
    layout_box: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export slide-image assets from a JSON manifest.")
    parser.add_argument("--image", help="Source slide image. Optional when manifest has source/images.")
    parser.add_argument("--manifest", required=True, help="JSON manifest describing assets to crop.")
    parser.add_argument("--out-dir", required=True, help="Output directory for PNG assets.")
    parser.add_argument("--contact-sheet", action="store_true", help="Write _contact_sheet.png.")
    parser.add_argument("--report", help="Write asset placement metadata JSON. Defaults to _assets_report.json.")
    return parser.parse_args()


def slug(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name).strip())
    return value.strip("._") or "asset"


def ensure_png(name: str) -> str:
    name = slug(name)
    return name if name.lower().endswith(".png") else f"{name}.png"


def load_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def color(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip().lstrip("#")
        if len(s) == 6:
            return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return np.array([float(value[0]), float(value[1]), float(value[2])], dtype=np.float32)
    raise ValueError(f"Unsupported color: {value!r}")


def normalized_crop_box(img: Image.Image, box: list[float]) -> list[int]:
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.width, x2), min(img.height, y2)
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid crop box after clipping: {box}")
    return [x1, y1, x2, y2]


def crop_box(img: Image.Image, box: list[float]) -> Image.Image:
    x1, y1, x2, y2 = normalized_crop_box(img, box)
    return img.crop((x1, y1, x2, y2))


def sample_corner_bg(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    sy = max(1, h // 10)
    sx = max(1, w // 10)
    samples = np.concatenate(
        [
            arr[:sy, :sx].reshape(-1, 3),
            arr[:sy, -sx:].reshape(-1, 3),
            arr[-sy:, :sx].reshape(-1, 3),
            arr[-sy:, -sx:].reshape(-1, 3),
        ],
        axis=0,
    )
    return np.median(samples, axis=0)


def alpha_bounds(img: Image.Image, pad: int = 4, min_alpha: int = 2) -> list[int]:
    arr = np.asarray(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > min_alpha)
    if len(xs) == 0:
        return [0, 0, img.width, img.height]
    x1 = max(0, int(xs.min()) - pad)
    y1 = max(0, int(ys.min()) - pad)
    x2 = min(img.width, int(xs.max()) + 1 + pad)
    y2 = min(img.height, int(ys.max()) + 1 + pad)
    return [x1, y1, x2, y2]


def trim_alpha_with_bounds(img: Image.Image, pad: int = 4, min_alpha: int = 2) -> tuple[Image.Image, list[int]]:
    x1, y1, x2, y2 = alpha_bounds(img, pad=pad, min_alpha=min_alpha)
    return img.crop((x1, y1, x2, y2)), [x1, y1, x2, y2]


def trim_alpha(img: Image.Image, pad: int = 4, min_alpha: int = 2) -> Image.Image:
    trimmed, _ = trim_alpha_with_bounds(img, pad=pad, min_alpha=min_alpha)
    return trimmed


def postprocess_alpha(alpha: np.ndarray, asset: dict[str, Any]) -> np.ndarray:
    """Apply optional alpha cleanup while keeping defaults conservative."""
    out = np.clip(alpha, 0, 255).astype(np.uint8)
    grow = int(asset.get("grow", asset.get("dilate", 0)) or 0)
    shrink = int(asset.get("shrink", asset.get("erode", 0)) or 0)
    if grow > 0:
        size = grow * 2 + 1
        out = np.asarray(Image.fromarray(out).filter(ImageFilter.MaxFilter(size)), dtype=np.uint8)
    if shrink > 0:
        size = shrink * 2 + 1
        out = np.asarray(Image.fromarray(out).filter(ImageFilter.MinFilter(size)), dtype=np.uint8)
    blur = float(asset.get("alpha_blur", asset.get("feather", 0)) or 0)
    if blur > 0:
        out = np.asarray(Image.fromarray(out).filter(ImageFilter.GaussianBlur(blur)), dtype=np.uint8)
    gamma = asset.get("alpha_gamma")
    if gamma is not None:
        gamma_value = max(0.05, float(gamma))
        arr = out.astype(np.float32) / 255.0
        out = np.clip((arr ** gamma_value) * 255, 0, 255).astype(np.uint8)
    if "alpha_floor" in asset:
        floor = float(asset["alpha_floor"])
        out = np.where(out > 0, np.maximum(out, floor), 0).astype(np.uint8)
    return out


def remove_solid_bg(
    img: Image.Image,
    bg: np.ndarray | None = None,
    transparent: float = 5,
    opaque: float = 38,
    trim: bool = True,
    pad: int = 4,
) -> Image.Image:
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).astype(np.float32)
    bg = sample_corner_bg(img) if bg is None else bg
    diff = np.max(np.abs(arr[:, :, :3] - bg), axis=2)
    alpha = np.clip((diff - transparent) / max(1, opaque - transparent) * 255, 0, 255)
    arr[:, :, 3] = alpha
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return trim_alpha(out, pad=pad) if trim else out


def purple_mask(arr: np.ndarray) -> np.ndarray:
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)
    return (r < 165) & (g < 105) & (b < 185) & (b > r * 0.75)


def dark_mask(arr: np.ndarray) -> np.ndarray:
    return (arr[:, :, 0] < 150) & (arr[:, :, 1] < 120) & (arr[:, :, 2] < 170)


def orange_mask(arr: np.ndarray) -> np.ndarray:
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)
    return (r > 130) & (g > 45) & (g < 205) & (b < 125) & (r > g * 1.08) & (g > b * 1.15)


def white_mask(arr: np.ndarray) -> np.ndarray:
    rgb = arr.astype(np.float32)
    return (rgb.min(axis=2) > 165) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 95)


def bright_mask(arr: np.ndarray, threshold: float = 135) -> np.ndarray:
    return arr.astype(np.float32).max(axis=2) > threshold


def mask_by_kind(arr: np.ndarray, kind: str, asset: dict[str, Any]) -> np.ndarray:
    if kind == "dark":
        return dark_mask(arr)
    if kind == "non-bg":
        bg = color(asset.get("bg"))
        if bg is None:
            bg = sample_corner_bg(Image.fromarray(arr))
        return np.max(np.abs(arr.astype(np.float32) - bg), axis=2) > float(asset.get("transparent", 8))
    if kind == "orange":
        return orange_mask(arr)
    if kind == "white":
        return white_mask(arr)
    if kind == "bright":
        return bright_mask(arr, float(asset.get("threshold", 135)))
    if kind == "purple":
        return purple_mask(arr)
    raise ValueError(f"Unsupported mask kind: {kind!r}")


def mask_region(img: Image.Image, asset: dict[str, Any], trim: bool = True) -> Image.Image:
    arr = np.asarray(img.convert("RGB"))
    mask_kind = asset.get("mask", "purple")
    if isinstance(mask_kind, list):
        mask = np.zeros(arr.shape[:2], dtype=bool)
        for item in mask_kind:
            mask |= mask_by_kind(arr, str(item), asset)
    else:
        mask = mask_by_kind(arr, str(mask_kind), asset)

    if asset.get("row_fill_holes", False):
        filled = np.zeros(mask.shape, dtype=bool)
        for y in range(mask.shape[0]):
            xs = np.where(mask[y])[0]
            if len(xs) > 1:
                filled[y, xs.min():xs.max() + 1] = True
        mask = filled

    alpha = (mask.astype(np.uint8) * 255)
    rgb = arr.copy()
    if asset.get("blank", False):
        vals = arr[mask]
        fill_color = color(asset.get("fill"))
        if fill_color is None:
            fill_color = np.median(vals, axis=0) if len(vals) else np.array([80, 20, 100])
        rgb[:, :, :] = np.array(fill_color, dtype=np.uint8)
    alpha = postprocess_alpha(alpha, asset)
    out = Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8))
    return trim_alpha(out, pad=int(asset.get("pad", 4))) if trim else out


def luma_key_asset(img: Image.Image, asset: dict[str, Any]) -> Image.Image:
    rgba = np.asarray(img.convert("RGBA")).astype(np.float32)
    rgb = rgba[:, :, :3]
    channel = str(asset.get("channel", "max")).lower()
    if channel == "luma":
        key = rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722
    elif channel == "saturation":
        key = rgb.max(axis=2) - rgb.min(axis=2)
    else:
        key = rgb.max(axis=2)
    transparent = float(asset.get("transparent", 24))
    opaque = float(asset.get("opaque", 88))
    alpha = np.clip((key - transparent) / max(1, opaque - transparent) * 255, 0, 255)
    if asset.get("invert", False):
        alpha = 255 - alpha
    alpha = postprocess_alpha(alpha, asset)
    rgba[:, :, 3] = np.minimum(rgba[:, :, 3], alpha)
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8))


def ellipse_asset(img: Image.Image, asset: dict[str, Any], trim: bool = True) -> Image.Image:
    rgba = np.asarray(img.convert("RGBA")).copy()
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    rx = max(1, w / 2.0 - 1)
    ry = max(1, h / 2.0 - 1)
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    alpha = np.clip((1.02 - dist) * 255 / 0.04, 0, 255).astype(np.uint8)
    if asset.get("blank", False):
        fill_color = color(asset.get("fill"))
        if fill_color is None:
            inner = rgba[alpha > 200, :3]
            fill_color = np.median(inner, axis=0) if len(inner) else np.array([80, 20, 100])
        rgba[:, :, :3] = np.array(fill_color, dtype=np.uint8)
    rgba[:, :, 3] = alpha
    out = Image.fromarray(rgba)
    return trim_alpha(out, pad=int(asset.get("pad", 2))) if trim else out


def render_asset(source: Image.Image, asset: dict[str, Any]) -> RenderedAsset:
    source_box = normalized_crop_box(source, asset["box"])
    img = source.crop(tuple(source_box))
    mode = asset.get("mode", "transparent")
    default_trim = True
    default_pad = int(asset.get("pad", 4))
    if mode in {"keep", "crop"}:
        out = img.convert("RGBA")
        default_trim = False
    elif mode in {"transparent", "solid-bg", "white-bg"}:
        out = remove_solid_bg(
            img,
            bg=color(asset.get("bg")),
            transparent=float(asset.get("transparent", 5)),
            opaque=float(asset.get("opaque", 38)),
            trim=False,
            pad=0,
        )
    elif mode in {"mask", "mask-color", "solid-mask"}:
        out = mask_region(img, asset, trim=False)
    elif mode in {"ellipse", "circle"}:
        out = ellipse_asset(img, asset, trim=False)
        default_pad = int(asset.get("pad", 2))
    elif mode in {"luma-key", "lumakey", "bright-key", "dark-bg"}:
        out = luma_key_asset(img, asset)
    else:
        raise ValueError(f"Unknown asset mode {mode!r} for {asset.get('name')!r}")
    if bool(asset.get("trim", default_trim)):
        out, trim_box = trim_alpha_with_bounds(out, pad=default_pad)
    else:
        trim_box = [0, 0, out.width, out.height]
    layout_box = [
        source_box[0] + trim_box[0],
        source_box[1] + trim_box[1],
        trim_box[2] - trim_box[0],
        trim_box[3] - trim_box[1],
    ]
    return RenderedAsset(out, source_box, trim_box, layout_box)


def contact_sheet(files: list[Path], out_path: Path) -> None:
    thumbs: list[tuple[str, Image.Image]] = []
    for path in files:
        img = Image.open(path).convert("RGBA")
        scale = min(160 / img.width, 95 / img.height, 1)
        thumb = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        thumbs.append((path.name, thumb))
    cols = 4
    cell_w, cell_h = 210, 140
    rows = max(1, math.ceil(len(thumbs) / cols))
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (250, 250, 250, 255))
    draw = ImageDraw.Draw(sheet)
    for idx, (name, thumb) in enumerate(thumbs):
        col, row = idx % cols, idx // cols
        x0, y0 = col * cell_w, row * cell_h
        for yy in range(y0 + 8, y0 + 108, 12):
            for xx in range(x0 + 8, x0 + 188, 12):
                shade = 235 if ((xx // 12 + yy // 12) % 2 == 0) else 255
                draw.rectangle((xx, yy, xx + 11, yy + 11), fill=(shade, shade, shade, 255))
        px = x0 + (188 - thumb.width) // 2 + 8
        py = y0 + (100 - thumb.height) // 2 + 8
        sheet.alpha_composite(thumb, (px, py))
        draw.text((x0 + 8, y0 + 114), name[:30], fill=(35, 35, 35, 255))
    sheet.save(out_path)


def jobs_from_manifest(doc: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    if "images" in doc:
        return doc["images"]
    if "slides" in doc and all("assets" in slide for slide in doc["slides"]):
        return doc["slides"]
    source = doc.get("source") or args.image
    if not source:
        raise ValueError("Provide --image or source in manifest.")
    return [{"source": source, "assets": doc.get("assets", [])}]


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    doc = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    records: list[dict[str, Any]] = []
    jobs = jobs_from_manifest(doc, args)

    for job_idx, job in enumerate(jobs, start=1):
        source_path = Path(job["source"])
        if not source_path.is_absolute():
            source_path = (manifest_path.parent / source_path).resolve()
        source = load_image(source_path)
        if "out_dir" in job:
            job_out = Path(job["out_dir"])
            if not job_out.is_absolute():
                job_out = out_root / job_out
        else:
            job_out = out_root if len(jobs) == 1 else out_root / f"page_{job_idx:03d}"
        job_out.mkdir(parents=True, exist_ok=True)
        for i, asset in enumerate(job.get("assets", []), start=1):
            name = ensure_png(asset.get("name", f"{i:02d}_asset"))
            output = job_out / name
            rendered = render_asset(source, asset)
            rendered.image.save(output)
            written.append(output)
            records.append(
                {
                    "name": Path(name).stem,
                    "file": output.as_posix(),
                    "source": str(source_path),
                    "mode": asset.get("mode", "transparent"),
                    "source_box": rendered.crop_box,
                    "trim_box": rendered.trim_box,
                    "layout_box": rendered.layout_box,
                    "size": [rendered.image.width, rendered.image.height],
                    "layout_element": {
                        "type": "image",
                        "name": Path(name).stem,
                        "path": output.as_posix(),
                        "box": rendered.layout_box,
                    },
                }
            )

    if args.contact_sheet:
        if len({p.parent for p in written}) == 1:
            contact_sheet(written, next(iter({p.parent for p in written})) / "_contact_sheet.png")
        contact_sheet(written, out_root / "_contact_sheet.png")

    report = {"count": len(written), "files": [str(p) for p in written], "assets": records}
    report_path = Path(args.report) if args.report else out_root / "_assets_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    parents = {p.parent for p in written}
    if len(parents) == 1:
        local_report = next(iter(parents)) / "_assets_report.json"
        if local_report.resolve() != report_path.resolve():
            local_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
