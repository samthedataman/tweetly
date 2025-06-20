from PIL import Image
import requests
from io import BytesIO

# Since the image is provided in the chat, we'll need to save it first
# For now, I'll create a script that can convert a saved image

def create_icon_sizes(input_path):
    """Convert an image to multiple icon sizes for browser extension"""
    
    # Open the original image
    img = Image.open(input_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Define the sizes we need
    sizes = {
        'icon128.png': 128,
        'icon48.png': 48,
        'icon16.png': 16
    }
    
    # Create each size
    for filename, size in sizes.items():
        # Create a high-quality resize
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save the resized image
        resized.save(filename, 'PNG', optimize=True)
        print(f"Created {filename} ({size}x{size})")

if __name__ == "__main__":
    # You'll need to save the bunny image first as 'bunny.png' or similar
    # Then run: python convert_bunny_to_icons.py
    print("Please save the bunny image as 'bunny.png' first")
    print("Then uncomment the line below and run the script")
    # create_icon_sizes('bunny.png')