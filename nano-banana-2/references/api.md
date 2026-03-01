# nano-banana-2 API Reference

## Endpoint

```
fal-ai/nano-banana-2
```

## Authentication

Set the `FAL_KEY` environment variable:

```bash
export FAL_KEY="your-api-key"
```

## Input Schema

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | ✅ | - | Text prompt for image generation |
| `num_images` | integer | ❌ | 1 | Number of images to generate |
| `aspect_ratio` | enum | ❌ | auto | Aspect ratio of generated image |
| `resolution` | enum | ❌ | 1K | Resolution of generated image |
| `output_format` | enum | ❌ | png | Output format (jpeg/png/webp) |
| `seed` | integer | ❌ | random | Random seed for reproducibility |
| `enable_web_search` | boolean | ❌ | false | Enable web search for current info |
| `safety_tolerance` | enum | ❌ | 4 | Content moderation (1-6, 1=strict) |
| `sync_mode` | boolean | ❌ | false | Return as data URI |
| `limit_generations` | boolean | ❌ | true | Limit to 1 generation per round |

### Aspect Ratios

- `auto` - Let model decide based on prompt
- `21:9` - Ultrawide
- `16:9` - Widescreen
- `3:2` - Classic photo
- `4:3` - Standard
- `5:4` - Near square
- `1:1` - Square
- `4:5` - Portrait near square
- `3:4` - Portrait standard
- `2:3` - Portrait photo
- `9:16` - Vertical video

### Resolutions

- `0.5K` - 512px
- `1K` - 1024px
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
  "description": "Generated image description"
}
```

## Client Usage

### JavaScript/TypeScript

```javascript
import { fal } from "@fal-ai/client";

const result = await fal.subscribe("fal-ai/nano-banana-2", {
  input: {
    prompt: "A serene mountain landscape at sunset",
    aspect_ratio: "16:9",
    resolution: "2K"
  }
});

console.log(result.data.images[0].url);
```

### Python

```python
from fal_client import client

result = client.subscribe(
    "fal-ai/nano-banana-2",
    input={
        "prompt": "A serene mountain landscape at sunset",
        "aspect_ratio": "16:9",
        "resolution": "2K"
    }
)

print(result["images"][0]["url"])
```

### Queue-based (async)

```python
# Submit request
response = client.queue.submit(
    "fal-ai/nano-banana-2",
    input={"prompt": "..."}
)
request_id = response["request_id"]

# Check status
status = client.queue.status(
    "fal-ai/nano-banana-2",
    request_id=request_id
)

# Get result when complete
result = client.queue.result(
    "fal-ai/nano-banana-2",
    request_id=request_id
)
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| 401 | Invalid API key | Check FAL_KEY environment variable |
| 429 | Rate limit exceeded | Wait and retry |
| 500 | Server error | Retry with exponential backoff |

## Best Practices

1. **Prompt Engineering**
   - Be specific and descriptive
   - Include style, mood, lighting details
   - Avoid ambiguous terms

2. **Resolution Selection**
   - 0.5K: Quick previews
   - 1K: General use (default)
   - 2K: High quality images
   - 4K: Print/large display

3. **Aspect Ratio**
   - Use `auto` for natural composition
   - Match intended display format

4. **Seed Usage**
   - Set seed for reproducibility
   - Vary seed for variations on same prompt

## Pricing

See fal.ai pricing page for current rates:
https://fal.ai/pricing
