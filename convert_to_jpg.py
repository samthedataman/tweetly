#!/usr/bin/env python3
"""
Convert PNG icons to JPG (Note: PNG is recommended for Chrome extensions)
"""
from PIL import Image
import os

def convert_png_to_jpg(png_file, jpg_file):
    """Convert PNG to JPG with white background"""
    # Open PNG
    png_image = Image.open(png_file)
    
    # Create white background
    jpg_image = Image.new('RGB', png_image.size, (255, 255, 255))
    
    # Paste PNG over white background (handles transparency)
    if png_image.mode == 'RGBA':
        jpg_image.paste(png_image, (0, 0), png_image)
    else:
        jpg_image.paste(png_image, (0, 0))
    
    # Save as JPG with high quality
    jpg_image.save(jpg_file, 'JPEG', quality=95)
    print(f"Converted {png_file} to {jpg_file}")

# Convert existing PNGs to JPGs
files_to_convert = {
    'icon16.png': 'icon16.jpg',
    'icon48.png': 'icon48.jpg',
    'icon128.png': 'icon128.jpg'
}

for png_file, jpg_file in files_to_convert.items():
    if os.path.exists(png_file):
        convert_png_to_jpg(png_file, jpg_file)
    else:
        print(f"Warning: {png_file} not found")

print("\nNote: Chrome extensions require PNG for manifest icons!")
print("JPG files can only be used for other assets like screenshots.")