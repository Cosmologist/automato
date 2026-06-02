# watermask

Extract an RGBA watermark from multiple photos with different backgrounds.

The watermark must be at the exact same pixel position across all input images. More diverse backgrounds yield more accurate extraction.

## Setup

```bash
pip install Pillow numpy
```

## Usage

```bash
python watermask.py img1.jpg img2.jpg [output.png]
python watermask.py img1.jpg img2.jpg img3.jpg img4.jpg img5.jpg [output.png]
```

| Images | Watermark type    | Recommended backgrounds                      |
|--------|-------------------|----------------------------------------------|
| 2      | Grayscale         | Black + white                                |
| 3–5    | Color             | Different colors (black, white, red, green, blue…) |

Output defaults to `watermark.png` if omitted. Output is an RGBA PNG where RGB = original watermark color, A = alpha channel.

## Example

```bash
python watermask.py datasets/black.jpeg datasets/white.jpeg
```

## Algorithm

For each pixel, the per-channel minimum and maximum across all images are computed:

```
dark  = min(img₁, img₂, …)   — approximates watermark on black bg
light = max(img₁, img₂, …)   — approximates watermark on white bg
alpha = 1 − (light − dark) / 255
color = dark / alpha
```

The resulting RGBA watermark can be used for subtraction from other images.
