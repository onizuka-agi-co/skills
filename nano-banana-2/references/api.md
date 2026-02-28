# Nano Banana 2 API Reference

## Endpoint

```
fal-ai/nano-banana-2
```

## Authentication

Set `FAL_KEY` environment variable or pass credentials directly:

```python
from fal_client import AsyncClient

client = AsyncClient(credentials="YOUR_FAL_KEY")
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | - | Text description of the image to generate |
| `num_images` | integer | - | 1 | Number of images to generate |
| `seed` | integer | - | random | Random seed for reproducibility |
| `aspect_ratio` | enum | - | auto | Aspect ratio of generated image |
| `output_format` | enum | - | png | Output format: jpeg, png, webp |
| `safety_tolerance` | enum | - | 4 | Content moderation level (1-6) |
| `sync_mode` | boolean | - | false | Return as data URI |
| `resolution` | enum | - | 1K | Resolution: 0.5K, 1K, 2K, 4K |
| `limit_generations` | boolean | - | true | Limit to 1 generation per prompt |
| `enable_web_search` | boolean | - | false | Enable web search for latest info |

### Aspect Ratios

- `auto` - Let model decide based on prompt
- `21:9` - Ultra-wide
- `16:9` - Widescreen
- `3:2` - Classic photo
- `4:3` - Standard
- `5:4` - Near square
- `1:1` - Square
- `4:5` - Portrait
- `3:4` - Portrait
- `2:3` - Portrait
- `9:16` - Mobile/portrait

### Resolutions

- `0.5K` - 512px (fastest)
- `1K` - 1024px (default)
- `2K` - 2048px (high quality)
- `4K` - 4096px (highest quality)

## Output Schema

```json
{
  "images": [
    {
      "url": "https://...",
      "content_type": "image/png",
      "file_name": "nano-banana-2-t2i-output.png",
      "file_size": 123456,
      "width": 1024,
      "height": 1024
    }
  ],
  "description": ""
}
```

## Python Example

```python
import asyncio
from fal_client import AsyncClient

async def generate():
    client = AsyncClient(credentials="YOUR_FAL_KEY")

    result = await client.subscribe(
        "fal-ai/nano-banana-2",
        input={
            "prompt": "A serene mountain landscape at sunset",
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "num_images": 1,
        }
    )

    for img in result["images"]:
        print(f"Image URL: {img['url']}")

asyncio.run(generate())
```

## TypeScript Example

```typescript
import { fal } from "@fal-ai/client";

const result = await fal.subscribe("fal-ai/nano-banana-2", {
  input: {
    prompt: "A cyberpunk city at night",
    aspect_ratio: "21:9",
    resolution: "4K",
  },
});

console.log(result.data.images[0].url);
```

## Error Handling

Common errors:
- `401 Unauthorized` - Invalid or missing API key
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Model error, retry

## Rate Limits

Check fal.ai dashboard for current rate limits.

## Cost

Check fal.ai pricing page for current pricing.
