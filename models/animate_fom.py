#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
import numpy as np
from skimage.transform import resize
from skimage import img_as_ubyte
import torch
import imageio

# Add the Thin-Plate-Spline-Motion-Model directory to path
sys.path.insert(0, '/app/models/Thin-Plate-Spline-Motion-Model')

# Import functions from the TPS model's demo script
from demo import load_checkpoints, make_animation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Thin-Plate Spline Motion Model Animation')
    parser.add_argument('--input', required=True, help='Path to source image')
    parser.add_argument('--driver', required=True, help='Path to driving video')
    parser.add_argument('--output', required=True, help='Path to output animation')
    parser.add_argument('--config', default='/app/models/Thin-Plate-Spline-Motion-Model/config/vox-256.yaml', 
                        help='Path to config')
    parser.add_argument('--checkpoint', default='/app/models/Thin-Plate-Spline-Motion-Model/checkpoints/vox.pth.tar', 
                        help='Path to checkpoint')
    parser.add_argument('--cpu', action='store_true', help='Use CPU for inference')
    
    args = parser.parse_args()

    # Check if files exist
    if not os.path.exists(args.input):
        print(f"Error: Source image {args.input} not found")
        sys.exit(1)
    
    if not os.path.exists(args.driver):
        print(f"Error: Driving video {args.driver} not found")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"Error: Config file {args.config} not found")
        sys.exit(1)
    
    if not os.path.exists(args.checkpoint):
        print(f"Error: Checkpoint file {args.checkpoint} not found")
        sys.exit(1)

    # Set device
    if args.cpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        device = torch.device('cpu')
    else:
        device = torch.device('cuda:0')

    # Load configuration
    with open(args.config) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # Load model
    print("Loading model checkpoints...")
    generator, kp_detector = load_checkpoints(config_path=args.config, 
                                             checkpoint_path=args.checkpoint,
                                             cpu=args.cpu)

    # Read source image
    print(f"Reading source image: {args.input}")
    source_image = imageio.imread(args.input)
    source_image = resize(source_image, (256, 256))[..., :3]
    
    # Read driving video
    print(f"Reading driving video: {args.driver}")
    reader = imageio.get_reader(args.driver)
    fps = reader.get_meta_data()['fps']
    driving_video = []
    try:
        for im in reader:
            driving_video.append(resize(im, (256, 256))[..., :3])
    except RuntimeError:
        pass
    reader.close()
    
    # Generate animation
    print("Generating animation...")
    predictions = make_animation(source_image, 
                                driving_video, 
                                generator, 
                                kp_detector, 
                                device=device)
    
    # Save result
    print(f"Saving animation to: {args.output}")
    imageio.mimsave(args.output, 
                   [img_as_ubyte(frame) for frame in predictions], 
                   fps=fps)
    
    print(f"Animation saved to {args.output}")