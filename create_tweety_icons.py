#!/usr/bin/env python3
"""
Create Tweety Bird icons for Chrome extension from the provided image
"""
import requests
from PIL import Image
import io

def download_and_resize_image(url, sizes):
    """Download image from URL and create icons in different sizes"""
    
    # For this example, I'll create a simple Tweety-inspired icon
    # In production, you would use the actual image URL or file
    
    # Create a Tweety-inspired icon with transparent background
    for size in sizes:
        # Create new image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # Note: In a real scenario, you would:
        # 1. Load your Tweety image
        # 2. Resize it to fit the icon size
        # 3. Save with transparent background
        
        # For now, let's create a placeholder that represents Tweety
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Draw a yellow circle for Tweety's head
        margin = size // 8
        head_bounds = [margin, margin, size - margin, size - margin]
        
        # Yellow body/head
        draw.ellipse(head_bounds, fill='#FFD700')
        
        # Add a simple "T" for Tweety in the center
        text_size = size // 3
        text_x = size // 2 - text_size // 4
        text_y = size // 2 - text_size // 2
        
        # Draw a simple T
        draw.rectangle([text_x, text_y, text_x + 4, text_y + text_size], fill='#FF6B35')
        draw.rectangle([text_x - text_size//3, text_y, text_x + text_size//3 + 4, text_y + 4], fill='#FF6B35')
        
        # Save as PNG
        filename = f'icon{size}.png'
        img.save(filename, 'PNG')
        print(f'Created {filename}')

# Create icons in required sizes
sizes = [16, 48, 128]
download_and_resize_image(None, sizes)

print("\nTweety icons created!")
print("\nTo use your actual Tweety image:")
print("1. Save your Tweety image as 'tweety_original.png'")
print("2. Run this command:")
print("   python -c \"from PIL import Image; img = Image.open('tweety_original.png'); img.resize((128, 128), Image.Resampling.LANCZOS).save('icon128.png'); img.resize((48, 48), Image.Resampling.LANCZOS).save('icon48.png'); img.resize((16, 16), Image.Resampling.LANCZOS).save('icon16.png')\"")