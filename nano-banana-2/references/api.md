# Nano Banana 2 API Reference

## Endpoint

```
fal-ai/nano-banana-2
```

## Authentication

Set `FAL_KEY` environment variable or create `~/fal-key.txt` file.

```bash
export FAL_KEY="your-api-key"
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text description of the image |
| `num_images` | integer | No | 1 | Number of images to generate (1-4) |
| `aspect_ratio` | enum | No | auto | Aspect ratio |
| `resolution` | enum | No | 1K | Resolution quality |
| `output_format` | enum | No | png | Output image format |
| `seed` | integer | No | random | Random seed for reproducibility |
| `enable_web_search` | boolean | No | false | Enable web search for up-to-date info |
| `safety_tolerance` | enum | No | 4 | Content moderation (1-6) |
| `sync_mode` | boolean | No | false | Return as data URI |

### Aspect Ratio Options

- `auto` - Let model decide based on prompt
- `21:9` - Ultra-wide
- `16:9` - Widescreen
- `3:2` - Classic photo
- `4:3` - Standard
- `5:4` - Portrait
- `1:1` - Square
- `4:5` - Portrait
- `3:4` - Portrait
- `2:3` - Portrait
- `9:16` - Vertical video

### Resolution Options

- `0.5K` - 512px (fastest)
- `1K` - 1024px (default)
- `2K` - 2048px (high quality)
- `4K` - 4096px (highest quality)

### Output Format Options

- `png` - Lossless, larger files
- `jpeg` - Lossy, smaller files
- `webp` - Modern format, good compression

## Output Schema

```json
{
  "images": [
    {
      "url": "https://...",
      "content_type": "image/png",
      "file_name": "nano-banana-2-t2i-output.png",
      "width": 1024,
      "height": 1024
    }
  ],
  "description": "Optional description"
}
```

## Example Request

```python
from fal_client import client

result = client.subscribe(
    "fal-ai/nano-banana-2",
    input={
        "prompt": "A serene mountain landscape at sunset",
        "aspect_ratio": "16:9",
        "resolution": "2K",
    },
)

for img in result["images"]:
    print(img["url"])
```

## Rate Limits

- Free tier: Limited requests per day
- Paid tier: Higher limits

## Pricing

Check fal.ai for current pricing.
