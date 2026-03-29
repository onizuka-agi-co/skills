# nano-banana-2 API Reference

## Overview

nano-banana-2 is a text-to-image model by fal.ai that generates high-quality images from text prompts.

## Installation

```bash
pip install fal-client
```

## Authentication

Set the `FAL_KEY` environment variable:

```bash
export FAL_KEY="your-api-key"
```

Or save to `~/fal-key.txt` in the workspace.

## Usage

### Python (Recommended)

```python
import fal_client

result = fal_client.subscribe(
    "fal-ai/nano-banana-2",
    arguments={
        "prompt": "A serene mountain landscape at sunset",
        "aspect_ratio": "16:9",
        "resolution": "2K",
    },
)

print(result["images"][0]["url"])
```

### CLI

```bash
uv run scripts/generate.py --prompt "Your prompt here"
```

## Input Schema

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | Text description of the image |
| `num_images` | integer | 1 | Number of images to generate (1-4) |
| `aspect_ratio` | string | auto | Aspect ratio of the image |
| `resolution` | string | 1K | Resolution: 0.5K, 1K, 2K, 4K |
| `output_format` | string | png | Format: jpeg, png, webp |
| `seed` | integer | random | Seed for reproducibility |
| `enable_web_search` | boolean | false | Enable web search for current info |
| `safety_tolerance` | string | 4 | Content moderation level (1-6) |
| `sync_mode` | boolean | false | Return as data URI |
| `limit_generations` | boolean | true | Limit to 1 generation per prompt |
| `thinking_level` | string | null | Enable model thinking: minimal, high |

### Aspect Ratios

| Ratio | Description |
|-------|-------------|
| auto | Let model decide |
| 21:9 | Ultrawide |
| 16:9 | Widescreen |
| 3:2 | Classic photo |
| 4:3 | Standard |
| 5:4 | Portrait standard |
| 1:1 | Square |
| 4:5 | Portrait |
| 3:4 | Portrait tall |
| 2:3 | Portrait taller |
| 9:16 | Vertical mobile |
| 4:1 | Panoramic |
| 1:4 | Ultra vertical |
| 8:1 | Super wide |
| 1:8 | Super tall |

## Output Schema

```json
{
  "images": [
    {
      "url": "https://...",
      "content_type": "image/png",
      "file_name": "generated.png",
      "file_size": 1234567,
      "width": 1024,
      "height": 1024
    }
  ],
  "description": "",
  "request_id": "uuid"
}
```

## Error Handling

| Code | Description |
|------|-------------|
| 400 | Invalid request parameters |
| 401 | Invalid or missing API key |
| 429 | Rate limit exceeded |
| 500 | Server error |

## Tips

1. **Be specific**: Detailed prompts yield better results
2. **Use web search**: For current events or specific entities
3. **Set seed**: For reproducible results
4. **Choose resolution**: Higher resolution takes longer

## Links

- [fal.ai nano-banana-2](https://fal.ai/models/fal-ai/nano-banana-2)
- [API Documentation](https://fal.ai/models/fal-ai/nano-banana-2/api)
