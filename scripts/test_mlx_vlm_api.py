#!/usr/bin/env python
"""Test MLX VLM Python API with Qwen2-VL-7B-Instruct-4bit (known working vision model)."""

from pathlib import Path

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

# Find a test image
test_folder = Path(
    "~/Creative Cloud Files  wilkins.keith@gmail.com 1853487558315A8D0A495ED5@AdobeID/Midjourney"
).expanduser()

if not test_folder.exists():
    print(f"❌ Folder not found: {test_folder}")
    exit(1)

images = list(test_folder.glob("*.png"))[:1] + list(test_folder.glob("*.jpg"))[:1]
if not images:
    print("❌ No test images found")
    exit(1)

test_image = images[0]
print(f"Testing with: {test_image.name}")
print(f"Size: {test_image.stat().st_size / 1024:.1f} KB\n")

# Load model (Qwen2-VL-7B - known working vision model)
print("Loading Qwen2-VL-7B-Instruct-4bit (vision model)...")
print("This may take a few minutes to download (~4GB)...\n")
model_path = "mlx-community/Qwen2-VL-7B-Instruct-4bit"
model, processor = load(model_path)
config = load_config(model_path)
print("✅ Model loaded\n")

# Test prompt
prompt = "Describe this image in 2-3 sentences."

# Format prompt
formatted_prompt = apply_chat_template(
    processor, config, prompt, num_images=1
)

print("Generating response...")
output = generate(
    model,
    processor,
    formatted_prompt,
    image=[str(test_image)],
    verbose=False,
    max_tokens=150,
    temp=0.5,
)

print("\n✅ Vision API working!")
print(f"\nResponse:\n{output}")
