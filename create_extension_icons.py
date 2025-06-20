from PIL import Image
import os

def create_extension_icons(input_image_path):
    """
    Convert an image to the three standard Chrome extension icon sizes.
    
    Args:
        input_image_path: Path to the input image (PNG, JPG, etc.)
    """
    
    # Check if input file exists
    if not os.path.exists(input_image_path):
        print(f"Error: Input file '{input_image_path}' not found!")
        return
    
    try:
        # Open the original image
        img = Image.open(input_image_path)
        
        # Convert to RGBA if not already (for transparency support)
        if img.mode != 'RGBA':
            # Create a new RGBA image with white background
            rgba_img = Image.new('RGBA', img.size, (255, 255, 255, 255))
            # Paste the original image
            if img.mode == 'P':  # Handle palette images
                img = img.convert('RGBA')
            rgba_img.paste(img, (0, 0))
            img = rgba_img
        
        # Define the sizes needed for Chrome extensions
        sizes = [
            (128, 'icon128.png'),
            (48, 'icon48.png'),
            (16, 'icon16.png')
        ]
        
        print(f"Original image size: {img.size}")
        print("Creating icon files...")
        
        for size, filename in sizes:
            # Create a square canvas
            square_size = (size, size)
            
            # Calculate scaling to fit the image
            img_ratio = img.width / img.height
            
            if img_ratio > 1:  # Wider than tall
                new_width = size
                new_height = int(size / img_ratio)
            else:  # Taller than wide or square
                new_height = size
                new_width = int(size * img_ratio)
            
            # Resize the image with high quality
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create a new transparent square image
            icon = Image.new('RGBA', square_size, (0, 0, 0, 0))
            
            # Paste the resized image in the center
            x_offset = (size - new_width) // 2
            y_offset = (size - new_height) // 2
            icon.paste(resized, (x_offset, y_offset))
            
            # Save the icon
            icon.save(filename, 'PNG', optimize=True)
            print(f"✓ Created {filename} ({size}x{size} pixels)")
        
        print("\nAll icons created successfully!")
        print("\nTo use these in your extension:")
        print('1. Add to manifest.json:')
        print('   "icons": {')
        print('     "16": "icon16.png",')
        print('     "48": "icon48.png",')
        print('     "128": "icon128.png"')
        print('   }')
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    print("Chrome Extension Icon Creator")
    print("=============================")
    print("\nThis script creates the 3 standard icon sizes for Chrome extensions.")
    print("\nUsage:")
    print("1. Save your bunny image as 'bunny.png' (or any name)")
    print("2. Run: python create_extension_icons.py")
    print("3. When prompted, enter the filename")
    print("\nOr call directly: create_extension_icons('your_image.png')")
    
    # Uncomment the lines below to use:
    # filename = input("\nEnter image filename (or press Enter for 'bunny.png'): ").strip()
    # if not filename:
    #     filename = 'bunny.png'
    # create_extension_icons(filename)