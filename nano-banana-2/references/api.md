# nano-banana-2 API Reference

## Endpoint

```
POST https://queue.fal.run/fal-ai/nano-banana-2
```

## Authentication

Include API key in Authorization header:

```
Authorization: Key YOUR_FAL_KEY
```

## Request Schema

```json
{
  "prompt": "string (required)",
  "num_images": 1,
  "aspect_ratio": "auto",
  "resolution": "1K",
  "output_format": "png",
  "safety_tolerance": "4",
  "seed": null,
  "enable_web_search": false,
  "limit_generations": true
}
```

## Parameters

### prompt (required)
- Type: string
- Description: Text description of the image to generate

### num_images
- Type: integer
- Default: 1
- Description: Number of images to generate

### aspect_ratio
- Type: enum
- Default: "auto"
- Options: auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16
- Description: Aspect ratio of generated image

### resolution
- Type: enum
- Default: "1K"
- Options: 0.5K, 1K, 2K, 4K
- Description: Resolution of generated image

### output_format
- Type: enum
- Default: "png"
- Options: jpeg, png, webp
- Description: Output format of generated image

### safety_tolerance
- Type: enum
- Default: "4"
- Options: 1, 2, 3, 4, 5, 6
- Description: Content moderation level (1=strict, 6=permissive)

### seed
- Type: integer
- Default: random
- Description: Random seed for reproducibility

### enable_web_search
- Type: boolean
- Default: false
- Description: Enable web search for up-to-date information

### limit_generations
- Type: boolean
- Default: true
- Description: Limit generations to 1 per prompt round

## Response Schema

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

## Example Requests

### Basic
```bash
curl -X POST https://queue.fal.run/fal-ai/nano-banana-2 \
  -H "Authorization: Key YOUR_FAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains"}'
```

### With Options
```bash
curl -X POST https://queue.fal.run/fal-ai/nano-banana-2 \
  -H "Authorization: Key YOUR_FAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cyberpunk city at night",
    "aspect_ratio": "16:9",
    "resolution": "2K",
    "num_images": 2
  }'
```

## Error Responses

### 401 Unauthorized
Invalid or missing API key.

### 402 Payment Required
API quota exceeded.

### 400 Bad Request
Invalid request parameters.

## Rate Limits

Refer to fal.ai pricing page for current rate limits.
