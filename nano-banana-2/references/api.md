# Nano Banana 2 API Reference

## Endpoint

```
POST https://queue.fal.run/fal-ai/nano-banana-2
```

## Authentication

Include API key in Authorization header:

```python
headers = {
    "Authorization": f"Key {FAL_KEY}",
    "Content-Type": "application/json",
}
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text prompt for image generation |
| `num_images` | integer | No | 1 | Number of images to generate |
| `aspect_ratio` | enum | No | auto | Aspect ratio of generated image |
| `resolution` | enum | No | 1K | Resolution of generated image |
| `output_format` | enum | No | png | Output format (jpeg, png, webp) |
| `seed` | integer | No | random | Random seed for reproducibility |
| `enable_web_search` | boolean | No | false | Enable web search for latest info |
| `safety_tolerance` | enum | No | 4 | Content moderation (1-6, 1=strict) |
| `sync_mode` | boolean | No | false | Return as data URI |
| `limit_generations` | boolean | No | true | Limit to 1 generation per prompt |

### Aspect Ratio Options

```
auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16
```

### Resolution Options

```
0.5K, 1K, 2K, 4K
```

### Output Format Options

```
jpeg, png, webp
```

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
  "description": "Description of generated images"
}
```

## Request Flow

1. **Submit request** → Get `request_id`
2. **Poll status** → Wait for `COMPLETED`
3. **Get result** → Download images

### Submit Request

```python
import requests

response = requests.post(
    "https://queue.fal.run/fal-ai/nano-banana-2",
    headers={"Authorization": f"Key {FAL_KEY}"},
    json={
        "prompt": "A beautiful sunset over mountains",
        "aspect_ratio": "16:9",
        "resolution": "2K",
    }
)

request_id = response.json()["request_id"]
```

### Get Result

```python
response = requests.get(
    f"https://queue.fal.run/fal-ai/nano-banana-2/requests/{request_id}",
    headers={"Authorization": f"Key {FAL_KEY}"}
)

result = response.json()
# Check status: IN_QUEUE, IN_PROGRESS, COMPLETED, FAILED
```

## Using fal.ai Client

```javascript
import { fal } from "@fal-ai/client";

// Configure
fal.config({ credentials: "YOUR_FAL_KEY" });

// Generate
const result = await fal.subscribe("fal-ai/nano-banana-2", {
  input: {
    prompt: "A serene mountain landscape",
    aspect_ratio: "16:9",
    resolution: "2K",
  },
});

console.log(result.data.images[0].url);
```

## Error Handling

| Status | Description |
|--------|-------------|
| 400 | Invalid request parameters |
| 401 | Invalid or missing API key |
| 403 | Rate limit exceeded |
| 500 | Server error |

## Rate Limits

- Basic tier: Limited requests per minute
- Pro tier: Higher limits

Check fal.ai dashboard for current limits.
