#!/usr/bin/env python3
"""
Create placeholder icons for Chrome extension
"""
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing PIL...")
    import subprocess
    subprocess.check_call(["pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont

def create_icon(size):
    # Create a new image with a gradient background
    img = Image.new('RGB', (size, size), color='#1DA1F2')
    draw = ImageDraw.Draw(img)
    
    # Add a subtle gradient effect
    for i in range(size):
        color_value = int(29 + (i/size) * 30)  # Gradient from #1D to #3D
        color = f'#{color_value:02x}A1F2'
        draw.line([(0, i), (size, i)], fill=color)
    
    # Draw a white X shape (Twitter/X logo style)
    margin = size // 5
    line_width = max(2, size // 12)
    
    # Draw X with rounded ends
    draw.line([(margin, margin), (size-margin, size-margin)], fill='white', width=line_width)
    draw.line([(size-margin, margin), (margin, size-margin)], fill='white', width=line_width)
    
    # Add a subtle border
    border_color = '#0d7fbf'
    draw.rectangle([(0, 0), (size-1, size-1)], outline=border_color, width=1)
    
    # Add rounded corners effect
    corner_size = max(2, size // 16)
    draw.pieslice([(0, 0), (corner_size*2, corner_size*2)], 180, 270, fill='#1DA1F2')
    draw.pieslice([(size-corner_size*2, 0), (size, corner_size*2)], 270, 360, fill='#1DA1F2')
    draw.pieslice([(0, size-corner_size*2), (corner_size*2, size)], 90, 180, fill='#1DA1F2')
    draw.pieslice([(size-corner_size*2, size-corner_size*2), (size, size)], 0, 90, fill='#1DA1F2')
    
    return img

# Create icons in required sizes
sizes = {
    16: 'icon16.png',
    48: 'icon48.png',
    128: 'icon128.png'
}

for size, filename in sizes.items():
    icon = create_icon(size)
    icon.save(filename)
    print(f'Created {filename} ({size}x{size})')

print("\nIcons created successfully!")
print("You can now load the extension in Chrome.")