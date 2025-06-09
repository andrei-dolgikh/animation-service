#!/usr/bin/env python3
import os
import sys
import argparse
from PIL import Image, ImageEnhance, ImageOps
import imageio
import numpy as np

def create_simple_animation(input_image_path, output_path, frames=24):
    """Create a simple animation with zoom and brightness effects"""
    try:
        print(f"Creating simple animation from {input_image_path}")
        
        # Check if input file exists
        if not os.path.exists(input_image_path):
            print(f"Error: Input file {input_image_path} does not exist")
            return False
            
        # Open the image
        img = Image.open(input_image_path)
        
        # Ensure the image is in RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Create frames list
        frames_list = []
        
        # Generate animation frames
        for i in range(frames):
            # Calculate zoom and brightness factors using sine wave
            zoom_factor = 1 + 0.08 * np.sin(i * 2 * np.pi / frames)
            brightness_factor = 1 + 0.15 * np.sin(i * 2 * np.pi / frames)
            
            # Create a copy of the image
            frame = img.copy()
            
            # Apply zoom effect
            new_size = (int(frame.width * zoom_factor), int(frame.height * zoom_factor))
            zoomed_frame = frame.resize(new_size, Image.LANCZOS)
            
            # Crop back to original size (center crop)
            left = (zoomed_frame.width - img.width) // 2
            top = (zoomed_frame.height - img.height) // 2
            right = left + img.width
            bottom = top + img.height
            cropped_frame = zoomed_frame.crop((left, top, right, bottom))
            
            # Adjust brightness
            enhancer = ImageEnhance.Brightness(cropped_frame)
            brightened_frame = enhancer.enhance(brightness_factor)
            
            # Add a subtle wave effect
            if i % 2 == 0:
                brightened_frame = ImageOps.mirror(brightened_frame)
                
            # Add to frames list
            frames_list.append(np.array(brightened_frame))
        
        # Save as gif
        print(f"Saving animation to {output_path}")
        imageio.mimsave(output_path, frames_list, format='GIF', duration=0.1)
        print(f"Animation saved successfully to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error creating simple animation: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple Image Animation')
    parser.add_argument('--input', required=True, help='Path to input image')
    parser.add_argument('--output', required=True, help='Path to output GIF')
    parser.add_argument('--driver', help='Ignored for compatibility')  # Added for compatibility
    args = parser.parse_args()
    
    success = create_simple_animation(args.input, args.output)
    sys.exit(0 if success else 1)