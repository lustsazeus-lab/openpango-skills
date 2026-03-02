#!/usr/bin/env python3
"""
Computer Vision & Multimodal Skill for OpenPango
Allows agents to analyze images, charts, and extract text from images.
"""
import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# Try to import optional dependencies
try:
    import pytesseract
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_vision_api_key() -> str:
    """Get vision API key from environment."""
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    return key


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime_type(path: str) -> str:
    """Get MIME type from image path."""
    ext = Path(path).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return mime_types.get(ext, "image/jpeg")


def describe_image_openai(image_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Use OpenAI GPT-4o vision to describe image."""
    import urllib.request
    import urllib.error
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    image_data = encode_image(image_path)
    mime_type = get_image_mime_type(image_path)
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000,
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"OpenAI API error: {error_body}")


def describe_image_anthropic(image_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Use Anthropic Claude vision to describe image."""
    import urllib.request
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    image_data = encode_image(image_path)
    mime_type = get_image_mime_type(image_path)
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"Anthropic API error: {error_body}")


def describe_image(image_path: str, prompt: str = "Describe this image in detail.", provider: str = "auto") -> str:
    """Describe an image using vision models.
    
    Args:
        image_path: Path to the image file
        prompt: Custom prompt for the vision model
        provider: 'openai', 'anthropic', or 'auto' (tries OpenAI first)
    
    Returns:
        Text description of the image
    """
    if provider == "openai" or (provider == "auto" and os.environ.get("OPENAI_API_KEY")):
        return describe_image_openai(image_path, prompt)
    elif provider == "anthropic" or (provider == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        return describe_image_anthropic(image_path, prompt)
    else:
        raise ValueError("No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")


def extract_text_ocr(image_path: str, lang: str = "eng") -> str:
    """Extract text from image using OCR (Tesseract).
    
    Args:
        image_path: Path to the image file
        lang: Language code for OCR (default: eng)
    
    Returns:
        Extracted text from the image
    """
    if not HAS_PIL:
        raise ImportError("PIL and pytesseract are required for OCR. Install with: pip install pillow pytesseract")
    
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}")


def extract_text_simple(image_path: str) -> str:
    """Simple text extraction - returns error if OCR not available."""
    if HAS_PIL:
        return extract_text_ocr(image_path)
    else:
        raise ImportError("OCR not available. Install pillow and pytesseract for text extraction.")


def get_image_info(image_path: str) -> Dict[str, Any]:
    """Get basic image information (dimensions, format, size)."""
    if not HAS_PIL:
        raise ImportError("PIL is required. Install with: pip install pillow")
    
    image = Image.open(image_path)
    file_size = os.path.getsize(image_path)
    
    return {
        "path": image_path,
        "format": image.format,
        "mode": image.mode,
        "size": {
            "width": image.width,
            "height": image.height
        },
        "file_size_bytes": file_size
    }


def main():
    parser = argparse.ArgumentParser(description="Computer Vision Skill for OpenPango")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # describe command
    desc_parser = subparsers.add_parser("describe", help="Describe an image using vision AI")
    desc_parser.add_argument("image_path", help="Path to the image file")
    desc_parser.add_argument("--prompt", "-p", default="Describe this image in detail.", help="Custom prompt")
    desc_parser.add_argument("--provider", choices=["openai", "anthropic", "auto"], default="auto", help="Vision provider")
    
    # ocr command
    ocr_parser = subparsers.add_parser("ocr", help="Extract text from image using OCR")
    ocr_parser.add_argument("image_path", help="Path to the image file")
    ocr_parser.add_argument("--lang", "-l", default="eng", help="Language code for OCR")
    
    # info command
    info_parser = subparsers.add_parser("info", help="Get image information")
    info_parser.add_argument("image_path", help="Path to the image file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "describe":
            result = describe_image(args.image_path, args.prompt, args.provider)
            print(json.dumps({"description": result}, indent=2))
        
        elif args.command == "ocr":
            result = extract_text_ocr(args.image_path, args.lang)
            print(json.dumps({"text": result}, indent=2))
        
        elif args.command == "info":
            result = get_image_info(args.image_path)
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    main()
