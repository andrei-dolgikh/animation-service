import os
import sys
import argparse
import numpy as np
from skimage.transform import resize
from skimage import img_as_ubyte
import torch
import imageio
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, '/app/models/first-order-model')
from demo import load_checkpoints, make_animation

parser = argparse.ArgumentParser(description='First Order Motion Model Animation')
parser.add_argument('--input', required=True, help='Path to input image')
parser.add_argument('--driver', required=True, help='Path to driving video')
parser.add_argument('--output', required=True, help='Path to output GIF')
args = parser.parse_args()

if __name__ == "__main__":
    print(f"Animating {args.input} with {args.driver} to {args.output}")
    
    # Проверка наличия модели
    model_path = '/app/models/first-order-model/vox-cpk.pth.tar'
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found")
        sys.exit(1)
    
    # Проверка наличия входного изображения
    if not os.path.exists(args.input):
        print(f"Error: Input image {args.input} not found")
        sys.exit(1)
    
    # Проверка наличия драйвера
    if not os.path.exists(args.driver):
        print(f"Error: Driving video {args.driver} not found")
        sys.exit(1)
    
    # Загрузка контрольных точек модели
    generator, kp_detector = load_checkpoints(config_path='/app/models/first-order-model/config/vox-256.yaml', 
                                            checkpoint_path=model_path)
    
    # Чтение входного изображения
    source_image = imageio.imread(args.input)
    source_image = resize(source_image, (256, 256))[..., :3]
    
    # Чтение видео-драйвера
    driving_video = imageio.mimread(args.driver, memtest=False)
    driving_video = [resize(frame, (256, 256))[..., :3] for frame in driving_video]
    
    # Создание анимации
    print("Generating animation...")
    predictions = make_animation(source_image, driving_video, generator, kp_detector, 
                               relative=True, adapt_movement_scale=True)
    
    # Сохранение результата как GIF
    print("Saving animation as GIF...")
    imageio.mimsave(args.output, [img_as_ubyte(frame) for frame in predictions], 
                   format='GIF', duration=0.1)
    
    print(f"Animation saved to {args.output}")