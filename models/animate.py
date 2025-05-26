import os
import sys
import argparse
import numpy as np
import torch
import imageio
from skimage.transform import resize
from skimage import img_as_ubyte
import subprocess

parser = argparse.ArgumentParser(description='Animation Script')
parser.add_argument('--input', required=True, help='Path to input image')
parser.add_argument('--driver', required=True, help='Path to driving video')
parser.add_argument('--output', required=True, help='Path to output file')
parser.add_argument('--config', help='Path to config file', default='/app/models/Thin-Plate-Spline-Motion-Model/config/vox-256.yaml')
parser.add_argument('--checkpoint', help='Path to checkpoint file', default='/app/models/Thin-Plate-Spline-Motion-Model/checkpoints/vox.pth.tar')
parser.add_argument('--model', help='Which model to use', default='tpsmm')
args = parser.parse_args()

def animate_tpsmm():
    """Animate using Thin-Plate-Spline Motion Model"""
    if not os.path.exists(args.checkpoint):
        print(f"Checkpoint file {args.checkpoint} not found, falling back to First Order Motion Model")
        return animate_fom()
    
    sys.path.append('/app/models/Thin-Plate-Spline-Motion-Model')
    
    try:
        from demo import load_checkpoints, make_animation
        
        source_image = imageio.imread(args.input)
        reader = imageio.get_reader(args.driver)
        fps = reader.get_meta_data()['fps']
        driving_video = []
        for im in reader:
            driving_video.append(im)
        reader.close()
        
        source_image = resize(source_image, (256, 256))[..., :3]
        driving_video = [resize(frame, (256, 256))[..., :3] for frame in driving_video]
        
        generator, kp_detector = load_checkpoints(config_path=args.config, checkpoint_path=args.checkpoint)
        
        predictions = make_animation(source_image, driving_video, generator, kp_detector, relative=True)
        
        imageio.mimsave(args.output, [img_as_ubyte(frame) for frame in predictions], format='GIF', duration=1.0/fps)
        
        print(f"Animation saved to {args.output}")
        return True
    except Exception as e:
        print(f"Error animating with TPSMM: {e}")
        return animate_fom()

def animate_fom():
    """Animate using First Order Motion Model as fallback"""
    print("Using First Order Motion Model as fallback")
    try:
        cmd = [
            'python', 
            '/app/models/animate_fom.py',
            '--input', args.input,
            '--driver', args.driver,
            '--output', args.output
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running First Order Motion Model: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

if __name__ == "__main__":
    if args.model.lower() == 'fom':
        success = animate_fom()
    else:
        success = animate_tpsmm()
    
    if not success:
        print("Animation failed with both models")
        sys.exit(1)