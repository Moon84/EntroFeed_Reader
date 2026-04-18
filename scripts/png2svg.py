#!/usr/bin/env python3
"""Convert PNG logo to SVG using Potrace via potracer library."""

from PIL import Image
import subprocess
import tempfile
from pathlib import Path


def convert_png_to_svg(input_path: str, output_path: str, size: int = None):
    """Convert PNG to SVG using potrace."""
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        print(f"Error: {input_path} not found")
        return False

    # Load image and convert to grayscale
    img = Image.open(input_file).convert('L')
    
    # Resize if needed
    if size:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    with tempfile.NamedTemporaryFile(suffix='.pnm', delete=False) as tmp:
        tmp_path = tmp.name
        # Save as PNM (P5 = grayscale PPM)
        img.save(tmp_path, format='PPM')
    
    # Run potrace
    result = subprocess.run(
        ['potrace', '-s', '-b', 'svg', '-o', str(output_file), '--tight', tmp_path],
        capture_output=True,
        text=True
    )
    
    Path(tmp_path).unlink()
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False

    print(f"Converted: {input_path} -> {output_path}")
    return True


def main():
    base_path = Path(__file__).parent.parent / "src" / "assets"
    icons_path = Path(__file__).parent.parent / "src" / "static" / "icons"

    # Convert main logo (icon only)
    convert_png_to_svg(
        base_path / "EntroFeed_logo.png",
        base_path / "EntroFeed_logo_icon.svg",
        size=400
    )

    # Convert logo with name
    convert_png_to_svg(
        base_path / "EntroFeed_logo_w_name.png",
        base_path / "EntroFeed_logo.svg",
        size=800
    )

    # Create favicon
    convert_png_to_svg(
        base_path / "EntroFeed_logo.png",
        icons_path / "favicon.svg",
        size=64
    )

    print("\nDone! SVG files created.")


if __name__ == "__main__":
    main()
