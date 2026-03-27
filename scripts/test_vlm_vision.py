#!/usr/bin/env python
"""Quick test script to verify MLX VLM vision capabilities."""

import base64
import json
from pathlib import Path

import requests

# Find a test image
test_folders = [
    Path("~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Midjourney").expanduser(),
]

test_image = None
for folder in test_folders:
    if folder.exists():
        images = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
        if images:
            test_image = images[0]
            break

if not test_image:
    print("❌ No test image found")
    exit(1)

print(f"Testing with: {test_image.name}")
print(f"Size: {test_image.stat().st_size / 1024:.1f} KB")

# Encode image
with open(test_image, "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

print(f"Base64 encoded: {len(image_data)} chars")

# Send to MLX VLM
print("\nSending to MLX VLM...")

response = requests.post(
    "http://localhost:8080/v1/chat/completions",
    json={
        "model": "mlx-community/Qwen3.5-27B-4bit",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in 2-3 sentences."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ],
        "max_tokens": 150,
        "temperature": 0.5,
    },
    timeout=60,
)

if response.status_code == 200:
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    print("\n✅ Vision API working!")
    print(f"\nResponse:\n{content}")
else:
    print(f"\n❌ Request failed: {response.status_code}")
    print(response.text)
