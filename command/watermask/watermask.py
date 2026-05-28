#!/usr/bin/env python3
"""
Extract a watermark (RGBA) from multiple photos with different backgrounds.

The watermark must be in the exact same pixel position across all input images.
The more diverse the backgrounds, the more accurate the extraction.

How it works:
  For each pixel position, the script finds the darkest value across all
  images (approximates "watermark on pure black") and the lightest value
  (approximates "watermark on pure white").  From these, the alpha and
  foreground color of the watermark are recovered.

Usage:

  python watermask.py img1.jpg img2.jpg [img3.jpg ...] [output.png]

  - 2 images: enough when the watermark is grayscale (black + white bg)
  - 3–5 images: recommended for color watermarks; use different colored
    backgrounds (e.g. black, white, red, green, blue) to better constrain
    each RGB channel.
  - output.png is optional (default: watermark.png).

Example:

  python watermask.py datasets/black.jpeg datasets/white.jpeg
"""

import argparse
import sys
import numpy as np
from PIL import Image


def extract_watermark(paths: list[str], output_path: str) -> None:
    images = [Image.open(p).convert("RGB") for p in paths]

    ref_size = images[0].size
    for i, img in enumerate(images):
        if img.size != ref_size:
            raise ValueError(
                f"Image sizes differ: {paths[i]} is {img.size}, expected {ref_size}"
            )

    stack = np.stack([np.array(img, dtype=np.float32) for img in images], axis=0)

    dark = stack.min(axis=0)
    light = stack.max(axis=0)

    diff = light - dark
    alpha = 1.0 - diff / 255.0
    alpha = np.mean(alpha, axis=2)
    alpha = np.clip(alpha, 0.0, 1.0)

    mask = alpha > 0
    fg = np.divide(dark, alpha[..., None], where=mask[..., None], out=np.zeros_like(dark))

    y_indices, x_indices = np.where(alpha > 5 / 255.0)
    if len(y_indices) > 0 and len(x_indices) > 0:
        y0, y1 = y_indices.min(), y_indices.max() + 1
        x0, x1 = x_indices.min(), x_indices.max() + 1
        pad = 2
        y0, y1 = max(0, y0 - pad), min(alpha.shape[0], y1 + pad)
        x0, x1 = max(0, x0 - pad), min(alpha.shape[1], x1 + pad)
        fg = fg[y0:y1, x0:x1]
        alpha = alpha[y0:y1, x0:x1]

    fg = np.clip(np.round(fg), 0, 255).astype(np.uint8)
    alpha_uint8 = (np.clip(np.round(alpha * 255), 0, 255)).astype(np.uint8)

    result = np.dstack((fg, alpha_uint8))
    Image.fromarray(result, "RGBA").save(output_path)


def print_banner() -> None:
    print("=" * 60)
    print("  watermask — extract RGBA watermark from multiple photos")
    print("=" * 60)
    print("  Usage: python watermask.py img1.jpg img2.jpg [img3...] [output.png]")
    print()
    print("  Images:  2 for grayscale watermark (e.g. black + white bg)")
    print("           3–5 for color watermark (different colored backgrounds)")
    print("  Watermark must be at the same position in all images.")
    print("  Output defaults to watermark.png if omitted.")
    print()
    print("  Algorithm:")
    print("    Per-pixel min across images ≈ watermark on black bg")
    print("    Per-pixel max across images ≈ watermark on white bg")
    print("    alpha = 1 − (max − min) / 255,  color = min / alpha")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract watermark from multiple images on different backgrounds"
    )
    parser.add_argument("images", nargs="+", help="Input images (2–5) with watermark at the same position")
    parser.add_argument("output", nargs="?", default="watermark.png", help="Output path for RGBA watermark PNG (default: watermark.png)")
    args = parser.parse_args()

    if len(args.images) < 2:
        print_banner()
        parser.error("At least 2 input images are required")
    if len(args.images) > 5:
        parser.error("No more than 5 input images are supported")

    n = len(args.images)
    guide = "2 images: grayscale watermark (e.g. black + white bg)"
    if n >= 3:
        guide = f"{n} images: color watermark (different colored backgrounds)"

    print("=" * 60)
    print("  watermask — extract RGBA watermark from multiple photos")
    print("=" * 60)
    print(f"  Usage: python watermask.py {' '.join(args.images)} {args.output}")
    print(f"  Recommendation: {guide}")
    print()

    extract_watermark(args.images, args.output)
    print(f"  Watermark saved to {args.output}")
    print()


if __name__ == "__main__":
    main()
