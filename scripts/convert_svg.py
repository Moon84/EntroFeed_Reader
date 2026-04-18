#!/usr/bin/env python3
"""Convert PNG to SVG using Potrace, preserving aspect ratio."""

from PIL import Image
import subprocess
from pathlib import Path


def convert_png_to_svg(input_path, output_path, max_size=400):
    """Convert PNG to clean SVG using potrace, preserving aspect ratio."""
    img = Image.open(input_path).convert('L')
    original_w, original_h = img.size
    
    # Calculate scale to fit within max_size while preserving ratio
    scale = min(max_size / original_w, max_size / original_h)
    new_w = max(1, int(original_w * scale))
    new_h = max(1, int(original_h * scale))
    
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Save as P5 (binary) PPM
    with open('/tmp/temp.ppm', 'wb') as f:
        f.write(b'P5\n')
        f.write(f'{img.width} {img.height}\n'.encode())
        f.write(b'255\n')
        f.write(img.tobytes())
    
    # Run potrace
    result = subprocess.run([
        'potrace', '-s', '-b', 'svg', '-o', str(output_path), 
        '--tight', '-z', 'black', '/tmp/temp.ppm'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    print(f"Converted: {input_path.name} -> {output_path.name} ({new_w}x{new_h})")
    return True


def main():
    base = Path(__file__).parent.parent / "src" / "assets"
    icons = Path(__file__).parent.parent / "src" / "static" / "icons"
    
    # Convert with aspect ratio preserved
    convert_png_to_svg(base / "EntroFeed_logo.png", base / "EntroFeed_logo_icon.svg", 300)
    convert_png_to_svg(base / "EntroFeed_logo_w_name.png", base / "EntroFeed_logo.svg", 600)
    convert_png_to_svg(base / "EntroFeed_logo.png", icons / "favicon.svg", 64)
    
    print("Done!")


if __name__ == "__main__":
    main()
