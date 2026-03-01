# Nano Banana 2 API Reference

## Overview

Nano Banana 2 is a text-to-image model by fal.ai that generates images from text descriptions.

## Endpoint

```
POST https://queue.fal.run/fal-ai/nano-banana-2
```

## Authentication

Set the `FAL_KEY` environment variable:

```bash
export FAL_KEY="your-api-key"
```

Include in request header:

```
Authorization: Key YOUR_FAL_KEY
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text prompt for image generation |
| `num_images` | integer | No | 1 | Number of images to generate |
| `aspect_ratio` | enum | No | auto | Aspect ratio of the image |
| `resolution` | enum | No | 1K | Resolution of the image |
| `output_format` | enum | No | png | Output format |
| `seed` | integer | No | random | Random seed for reproducibility |
| `enable_web_search` | boolean | No | false | Enable web search |
| `safety_tolerance` | enum | No | 4 | Content moderation level (1-6) |
| `limit_generations` | boolean | No | true | Limit generations to 1 |
| `sync_mode` | boolean | No | false | Return as data URI |

### Aspect Ratio Options

- `auto` - Let the model decide
- `21:9` - Ultrawide
- `16:9` - Widescreen
- `3:2` - Classic photo
- `4:3` - Standard
- `5:4` - Portrait standard
- `1:1` - Square
- `4:5` - Portrait
- `3:4` - Portrait
- `2:3` - Portrait
- `9:16` - Vertical (mobile)

### Resolution Options

- `0.5K` - 512px
- `1K` - 1024px
- `2K` - 2048px
- `4K` - 4096px

### Output Format Options

- `jpeg` - JPEG format
- `png` - PNG format (lossless)
- `webp` - WebP format

### Safety Tolerance

- `1` - Most strict (blocks most content)
- `2-5` - Moderate levels
- `6` - Least strict

## Output Schema

```json
{
  "images": [
    {
      "url": "https://storage.googleapis.com/...",
      "content_type": "image/png",
      "file_name": "nano-banana-2-t2i-output.png",
      "file_size": 123456,
      "width": 1024,
      "height": 1024
    }
  ],
  "description": "Description of generated images"
}
```

## Example Request

```python
import requests

headers = {
    "Authorization": "Key YOUR_FAL_KEY",
    "Content-Type": "application/json",
}

payload = {
    "prompt": "A serene mountain landscape at sunset with a lake reflection",
    "num_images": 1,
    "aspect_ratio": "16:9",
    "resolution": "2K",
    "output_format": "png"
}

response = requests.post(
    "https://queue.fal.run/fal-ai/nano-banana-2",
    headers=headers,
    json=payload
)

result = response.json()
print(result["images"][0]["url"])
```

## JavaScript/TypeScript Client

```typescript
import { fal } from "@fal-ai/client";

const result = await fal.subscribe("fal-ai/nano-banana-2", {
  input: {
    prompt: "A serene mountain landscape at sunset",
    aspect_ratio: "16:9",
    resolution: "2K",
  },
});

console.log(result.data.images[0].url);
```

## Error Handling

Common errors:

- `401 Unauthorized` - Invalid or missing API key
- `400 Bad Request` - Invalid parameters
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server-side error

## Rate Limits

Refer to fal.ai documentation for current rate limits.

## Pricing

Refer to fal.ai pricing page for current pricing.
