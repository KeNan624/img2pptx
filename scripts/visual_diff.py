#!/usr/bin/env python
"""Compare a rendered PPT preview against the source slide image."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate visual diff metrics and heatmaps.")
    parser.add_argument("--source", required=True, help="Reference source image.")
    parser.add_argument("--preview", required=True, help="Rendered PPT preview image.")
    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--tile", type=int, default=48, help="Tile size for top mismatch regions.")
    parser.add_argument("--report", help="Optional report JSON path.")
    return parser.parse_args()


def load_rgb(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def global_ssim(a: np.ndarray, b: np.ndarray) -> float:
    x = a.astype(np.float64)
    y = b.astype(np.float64)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mux = x.mean()
    muy = y.mean()
    sigx = ((x - mux) ** 2).mean()
    sigy = ((y - muy) ** 2).mean()
    sigxy = ((x - mux) * (y - muy)).mean()
    return float(((2 * mux * muy + c1) * (2 * sigxy + c2)) / ((mux**2 + muy**2 + c1) * (sigx + sigy + c2)))


def heatmap(diff: np.ndarray) -> Image.Image:
    norm = np.clip(diff / max(1.0, np.percentile(diff, 98)), 0, 1)
    h, w = norm.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = np.clip(norm * 255, 0, 255).astype(np.uint8)
    rgba[:, :, 1] = np.clip((1 - np.abs(norm - 0.5) * 2) * 170, 0, 170).astype(np.uint8)
    rgba[:, :, 3] = np.clip(norm * 230, 0, 230).astype(np.uint8)
    return Image.fromarray(rgba).filter(ImageFilter.GaussianBlur(0.6))


def top_tiles(diff: np.ndarray, tile: int, limit: int = 12) -> list[dict[str, float | list[int]]]:
    h, w = diff.shape
    rows: list[dict[str, float | list[int]]] = []
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            region = diff[y : min(h, y + tile), x : min(w, x + tile)]
            rows.append({"box": [x, y, region.shape[1], region.shape[0]], "mae": float(region.mean())})
    rows.sort(key=lambda item: float(item["mae"]), reverse=True)
    return rows[:limit]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = load_rgb(args.source)
    preview = load_rgb(args.preview)
    if preview.size != source.size:
        preview = preview.resize(source.size, Image.LANCZOS)

    src = np.asarray(source).astype(np.float32)
    prv = np.asarray(preview).astype(np.float32)
    delta = np.abs(src - prv)
    diff = delta.mean(axis=2)
    mae = float(diff.mean())
    rmse = float(math.sqrt(((src - prv) ** 2).mean()))
    psnr = float("inf") if rmse == 0 else float(20 * math.log10(255.0 / rmse))
    ssim = global_ssim(src.mean(axis=2), prv.mean(axis=2))
    tiles = top_tiles(diff, args.tile)

    heat = heatmap(diff)
    heat_path = out_dir / "diff_heatmap.png"
    heat.save(heat_path)
    overlay = source.convert("RGBA")
    overlay.alpha_composite(heat)
    draw = ImageDraw.Draw(overlay)
    for item in tiles[:6]:
        x, y, w, h = [int(v) for v in item["box"]]
        draw.rectangle((x, y, x + w, y + h), outline=(255, 255, 0, 230), width=2)
    overlay_path = out_dir / "diff_overlay.png"
    overlay.save(overlay_path)

    report = {
        "source": str(args.source),
        "preview": str(args.preview),
        "source_size": list(source.size),
        "mae": mae,
        "rmse": rmse,
        "psnr": psnr,
        "ssim": ssim,
        "top_regions": tiles,
        "heatmap": str(heat_path),
        "overlay": str(overlay_path),
    }
    report_path = Path(args.report) if args.report else out_dir / "visual_diff_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mae", "rmse", "psnr", "ssim", "heatmap", "overlay")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
