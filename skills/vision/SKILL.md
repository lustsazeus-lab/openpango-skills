---
name: vision
description: "Analyze images, charts, and extract text from images using vision models and OCR."
user-invocable: true
metadata: {"openclaw":{"emoji":"👁️","skillKey":"openpango-vision"}}
---

## Overview

This skill enables OpenPango agents to "see" by analyzing images with AI vision models and extracting text from images using OCR. Agents can describe images, analyze charts, read text from screenshots, and more.

## Setup

### Prerequisites

1. **For AI Vision**: Set at least one API key:
   ```bash
   # OpenAI (GPT-4o)
   export OPENAI_API_KEY="sk-..."
   
   # OR Anthropic (Claude 3.5 Sonnet)
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **For OCR** (optional): Install Tesseract:
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Python dependencies
   pip install pillow pytesseract
   ```

## Tools

### describe

Analyze an image using AI vision models.

```bash
python3 skills/vision/image_analyzer.py describe /path/to/image.jpg
```

With custom prompt:
```bash
python3 skills/vision/image_analyzer.py describe /path/to/image.jpg --prompt "What text is in this screenshot?"
```

With specific provider:
```bash
python3 skills/vision/image_analyzer.py describe /path/to/image.jpg --provider openai
python3 skills/vision/image_analyzer.py describe /path/to/image.jpg --provider anthropic
```

Returns:
```json
{
  "description": "The image shows a modern office space with natural lighting..."
}
```

### ocr

Extract text from images using OCR (Optical Character Recognition).

```bash
python3 skills/vision/image_analyzer.py ocr /path/to/screenshot.png
```

With specific language:
```bash
python3 skills/vision/image_analyzer.py ocr /path/to/german-text.png --lang deu
```

Returns:
```json
{
  "text": "Extracted text from the image..."
}
```

### info

Get basic image information.

```bash
python3 skills/vision/image_analyzer.py info /path/to/image.jpg
```

Returns:
```json
{
  "path": "/path/to/image.jpg",
  "format": "JPEG",
  "mode": "RGB",
  "size": {
    "width": 1920,
    "height": 1080
  },
  "file_size_bytes": 245678
}
```

## Common Use Cases

### Analyze a Screenshot

```bash
python3 skills/vision/image_analyzer.py describe screenshot.png --prompt "What UI elements are in this screenshot?"
```

### Extract Text from a Document

```bash
python3 skills/vision/image_analyzer.py ocr document-scan.png
```

### Analyze a Chart

```bash
python3 skills/vision/image_analyzer.py describe chart.png --prompt "Describe the data visualization and trends in this chart"
```

### Verify Visual Content

```bash
python3 skills/vision/image_analyzer.py describe verification.png --prompt "Does this image contain a specific logo or brand element?"
```

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)

## Error Handling

Returns errors as JSON:

```json
{
  "error": "OPENAI_API_KEY not set"
}
```

Or for missing dependencies:
```json
{
  "error": "PIL is required. Install with: pip install pillow"
}
```

## Integration with Agents

Agents can use this skill to:
- Analyze screenshots for debugging
- Extract text from scanned documents
- Describe charts and graphs
- Verify visual content matches expectations
- Read text from UI elements in screenshots
