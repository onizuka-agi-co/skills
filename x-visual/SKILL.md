---
name: x-visual
description: "Generate visual explanations for X (Twitter) posts. Use when: (1) creating visual summaries of tweets, (2) generating AI artwork from tweet content, (3) enhancing tweet explanations with images."
---

# X Visual - Tweet Visual Explanation Generator

Generate visual explanations for X (Twitter) posts using AI image generation.

## Quick Start

```bash
# Generate visual for a tweet
uv run scripts/x_visual.py explain <tweet_id>

# Generate with custom prompt
uv run scripts/x_visual.py explain <tweet_id> --prompt "Custom prompt"

# Generate and save locally
uv run scripts/x_visual.py explain <tweet_id> --output ./images/
```

## Commands

| Command | Description |
|---------|-------------|
| `explain <tweet_id>` | Generate visual explanation for a tweet |
| `batch <file>` | Process multiple tweets from JSON file |
| `preview <tweet_id>` | Preview prompt without generating |

## Workflow

1. **Fetch tweet** - Get tweet content using X API
2. **Analyze content** - Extract keywords, topics, and visual elements
3. **Generate prompt** - Create image generation prompt
4. **Generate image** - Use nano-banana-2 to create visual
5. **Create explanation** - Generate accompanying text

## Output

- Generated image (PNG/JPEG/WebP)
- Explanation text in Japanese
- Ready for posting to X/Discord

## Integration

This skill integrates with:
- **x-read**: Fetch tweet content
- **nano-banana-2**: Generate images
- **x-write**: Post results to X

## Resources

### scripts/
- `x_visual.py` - Main script for visual generation

### references/
- `prompts.md` - Prompt templates for different content types
