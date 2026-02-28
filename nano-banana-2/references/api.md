# Nano Banana 2 API Reference

## Endpoint

```
POST https://queue.fal.run/fal-ai/nano-banana-2
```

## Authentication

Set `FAL_KEY` environment variable or include in request header:

```
Authorization: Key YOUR_FAL_KEY
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | - | Text description of the image to generate |
| `num_images` | integer | ❌ | 1 | Number of images to generate |
| `aspect_ratio` | enum | ❌ | auto | Aspect ratio of the generated image |
| `resolution` | enum | ❌ | 1K | Resolution of the image |
| `output_format` | enum | ❌ | png | Output format (jpeg, png, webp) |
| `seed` | integer | ❌ | random | Random seed for reproducibility |
| `enable_web_search` | boolean | ❌ | false | Enable web search for latest info |
| `limit_generations` | boolean | ❌ | true | Limit generations to 1 per round |
| `safety_tolerance` | enum | ❌ | 4 | Content moderation (1-6, 1=strict) |
| `sync_mode` | boolean | ❌ | false | Return as data URI |

### Aspect Ratios

- `auto` - Let model decide based on prompt
- `21:9` - Ultrawide
- `16:9` - Widescreen
- `3:2` - Classic photo
- `4:3` - Standard
- `5:4` - Portrait standard
- `1:1` - Square
- `4:5` - Portrait
- `3:4` - Portrait tall
- `2:3` - Portrait taller
- `9:16` - Vertical (mobile)

### Resolutions

- `0.5K` - 512px
- `1K` - 1024px (default)
- `2K` - 2048px
- `4K` - 4096px

## Output Schema

```json
{
  "images": [
    {
      "url": "https://...",
      "content_type": "image/png",
      "file_name": "nano-banana-2-t2i-output.png",
      "file_size": 1234567,
      "width": 1024,
      "height": 1024
    }
  ],
  "description": ""
}
```

## Queue-Based Workflow

The API uses a queue-based system:

1. **Submit request** → Get `request_id`
2. **Poll status** → Check `status` field
3. **Get result** → When `status === "COMPLETED"`

### Status Values

- `IN_QUEUE` - Waiting in queue
- `IN_PROGRESS` - Being processed
- `COMPLETED` - Done, ready to fetch
- `FAILED` - Error occurred

## Example Request (JavaScript)

```javascript
import { fal } from "@fal-ai/client";

const result = await fal.subscribe("fal-ai/nano-banana-2", {
  input: {
    prompt: "A serene mountain landscape at sunset",
    aspect_ratio: "16:9",
    resolution: "2K",
    num_images: 1
  }
});

console.log(result.data.images[0].url);
```

## Example Request (Python)

```python
import httpx

api_key = "YOUR_FAL_KEY"
url = "https://queue.fal.run/fal-ai/nano-banana-2"

headers = {
    "Authorization": f"Key {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "prompt": "A serene mountain landscape at sunset",
    "aspect_ratio": "16:9",
    "resolution": "2K"
}

response = httpx.post(url, headers=headers, json=payload)
result = response.json()
print(result["images"][0]["url"])
```

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid request parameters |
| 401 | Invalid or missing API key |
| 429 | Rate limit exceeded |
| 500 | Server error |

## Rate Limits

- Free tier: Limited requests per minute
- Paid tier: Higher limits available

Check fal.ai pricing for current limits.
