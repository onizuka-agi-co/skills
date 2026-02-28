---
name: nano-banana-2
description: "Generate images from text prompts using fal.ai's nano-banana-2 model. Use when: (1) creating images from text descriptions, (2) generating AI artwork, (3) producing visual content from prompts. Supports multiple aspect ratios, resolutions (0.5K-4K), and output formats (PNG/JPEG/WebP)."
---

# Nano Banana 2

Generate images from text prompts using fal.ai's nano-banana-2 text-to-image model.

## Quick Start

```bash
# Basic usage
uv run scripts/generate.py --prompt "A serene mountain landscape at sunset"

# With options
uv run scripts/generate.py \
  --prompt "A cyberpunk city at night" \
  --aspect-ratio 16:9 \
  --resolution 2K \
  --num-images 2 \
  --output-format png
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | (required) | Text description of the image |
| `num_images` | int | 1 | Number of images to generate |
| `aspect_ratio` | enum | auto | Aspect ratio: auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16 |
| `resolution` | enum | 1K | Resolution: 0.5K, 1K, 2K, 4K |
| `output_format` | enum | png | Output format: jpeg, png, webp |
| `seed` | int | random | Random seed for reproducibility |
| `enable_web_search` | bool | false | Enable web search for up-to-date info |

## Setup

Set the `FAL_KEY` environment variable:

```bash
export FAL_KEY="your-api-key"
```

Or save to `~/fal-key.txt` in the workspace.

## Output

Returns image URLs that can be:
- Downloaded locally
- Displayed in chat
- Used in further processing

## Examples

**Portrait:**
```bash
uv run scripts/generate.py --prompt "A professional portrait of a woman" --aspect-ratio 4:5
```

**Landscape:**
```bash
uv run scripts/generate.py --prompt "A vast desert with sand dunes" --aspect-ratio 21:9 --resolution 4K
```

**Multiple images:**
```bash
uv run scripts/generate.py --prompt "Abstract art with vibrant colors" --num-images 4
```

## Resources

### scripts/
- `generate.py` - Main image generation script

### references/
- `api.md` - Detailed API documentation
