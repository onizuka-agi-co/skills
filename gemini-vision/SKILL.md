---
name: gemini-vision
description: "Analyze images and videos using Google Gemini Vision API. Use when: (1) analyzing single or multiple images, (2) extracting information from photos/screenshots, (3) summarizing or understanding video content, (4) OCR and text extraction from images, (5) comparing visual content, (6) structured data extraction from visual inputs. Works with local files and URLs."
---

# Gemini Vision

Analyze images and videos using Google's Gemini multimodal models.

## Quick Start

```bash
# Analyze an image
uv run skills/gemini-vision/scripts/gemini_vision.py image photo.jpg "Describe this image"

# Analyze multiple images
uv run skills/gemini-vision/scripts/gemini_vision.py image img1.jpg img2.jpg "Compare these"

# Analyze a video
uv run skills/gemini-vision/scripts/gemini_vision.py video clip.mp4 "Summarize the action"
```

## Requirements

1. **API Key**: Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable
2. **UV**: Python package manager (for dependency resolution)
3. **ffmpeg**: Required for video analysis (`apt install ffmpeg`)

Dependencies are auto-resolved by UV:
- `google-genai` - Google Gemini SDK
- `pillow` - Image processing

## Commands

### Image Analysis

```bash
# Single image
uv run gemini_vision.py image <path> "<prompt>"

# Multiple images (comparison)
uv run gemini_vision.py image img1.jpg img2.jpg "<prompt>"

# From URL
uv run gemini_vision.py image https://example.com/photo.jpg "<prompt>"
```

### Video Analysis

```bash
# Basic video analysis
uv run gemini_vision.py video video.mp4 "<prompt>"

# Control frame extraction
uv run gemini_vision.py video video.mp4 "<prompt>" --max-frames 20 --fps 2.0
```

## Options

| Option | Description |
|--------|-------------|
| `--model`, `-m` | Model name (default: `gemini-2.0-flash`) |
| `--json`, `-j` | Output as JSON |
| `--max-frames`, `-f` | Max frames for video (default: 10) |
| `--fps` | Frame extraction rate (default: 1.0) |

## Models

| Model | Use Case |
|-------|----------|
| `gemini-3-flash-preview` | Fast, efficient analysis (default) |
| `gemini-3-pro-preview` | Complex reasoning, detailed analysis |
| `gemini-2.5-flash` | Stable, fast alternative |
| `gemini-2.5-pro` | High accuracy analysis |

## Use Cases

### Image Analysis

```bash
# Describe an image
uv run gemini_vision.py image photo.jpg "Describe this image in detail"

# Extract text (OCR)
uv run gemini_vision.py image screenshot.png "Extract all text from this image"

# Identify objects
uv run gemini_vision.py image photo.jpg "List all objects visible"

# Get structured data
uv run gemini_vision.py image chart.png "Extract the data as JSON" --json
```

### Video Analysis

```bash
# Summarize a video
uv run gemini_vision.py video lecture.mp4 "Summarize the key points"

# Identify actions
uv run gemini_vision.py video sports.mp4 "Describe the actions happening"

# Extract information
uv run gemini_vision.py video demo.mp4 "List the steps demonstrated"
```

### Comparison

```bash
# Compare images
uv run gemini_vision.py image before.jpg after.jpg "What changed between these images?"

# Find differences
uv run gemini_vision.py image design1.png design2.png "List all visual differences"
```

## Error Handling

- **API key not set**: Ensure `GEMINI_API_KEY` or `GOOGLE_API_KEY` is exported
- **ffmpeg not found**: Install with `apt install ffmpeg` or `brew install ffmpeg`
- **File not found**: Check path is correct and accessible
- **Rate limits**: Wait and retry, or use a different API key

## API Key Setup

1. Go to https://aistudio.google.com/app/apikey
2. Create an API key
3. Export in shell:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
4. Or add to `~/.bashrc` or `~/.zshrc` for persistence
