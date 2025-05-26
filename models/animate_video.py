import os
import sys
import argparse
import torch
import yaml
import numpy as np
from PIL import Image
import imageio
from skimage.transform import resize
from skimage import img_as_ubyte

# Парсинг аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument("--input", help="Path to input image")
parser.add_argument("--output", help="Path to output video")
parser.add_argument("--driver", default="/app/models/driving_video.mp4", help="Path to driving video")
parser.add_argument("--config", default="/app/models/Thin-Plate-Spline-Motion-Model/config/vox-256.yaml", help="Path to config")
parser.add_argument("--checkpoint", default="/app/models/Thin-Plate-Spline-Motion-Model/checkpoints/vox.pth.tar", help="Path to checkpoint")
args = parser.parse_args()

# Добавляем путь к модели в PYTHONPATH
sys.path.append('/app/models/Thin-Plate-Spline-Motion-Model')

# Импортируем модули из модели
from modules.generator import OcclusionAwareGenerator
from modules.keypoint_detector import KPDetector
from animate import normalize_kp

# Загрузка конфигурации модели
def load_config(config_path):
    with open(config_path) as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    return config

# Загрузка контрольных точек модели
def load_checkpoints(config_path, checkpoint_path, cpu=False):
    config = load_config(config_path)
    
    generator = OcclusionAwareGenerator(**config['model_params']['generator_params'],
                                        **config['model_params']['common_params'])
    
    kp_detector = KPDetector(**config['model_params']['kp_detector_params'],
                             **config['model_params']['common_params'])
    
    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu') if cpu else None)
    
    generator.load_state_dict(checkpoint['generator'])
    kp_detector.load_state_dict(checkpoint['kp_detector'])
    
    if not cpu:
        generator.cuda()
        kp_detector.cuda()
    
    generator.eval()
    kp_detector.eval()
    
    return generator, kp_detector

# Чтение кадров из видео
def read_video(video_path):
    video = imageio.get_reader(video_path)
    frames = []
    try:
        for im in video:
            frames.append(im)
    except RuntimeError:
        pass
    return frames

# Создание анимации
def animate(source_image_path, driving_video_path, output_path, generator, kp_detector, relative=True, adapt_movement_scale=True):
    print(f"Processing source image: {source_image_path}")
    print(f"Using driving video: {driving_video_path}")
    
    # Чтение исходного изображения
    source_image = imageio.imread(source_image_path)
    source_image = resize(source_image, (256, 256))[..., :3]
    
    # Чтение видео-драйвера
    driving_video = read_video(driving_video_path)
    
    # Предварительная обработка кадров
    source = torch.tensor(source_image[np.newaxis].astype(np.float32)).permute(0, 3, 1, 2)
    if torch.cuda.is_available():
        source = source.cuda()
    
    driving = torch.tensor(np.array(driving_video)[np.newaxis].astype(np.float32)).permute(0, 4, 1, 2, 3)
    
    kp_source = kp_detector(source)
    
    # Генерация анимации
    predictions = []
    
    for frame_idx in range(driving.shape[2]):
        print(f"\rProcessing frame {frame_idx}/{driving.shape[2]}", end="")
        
        driving_frame = driving[:, :, frame_idx]
        if torch.cuda.is_available():
            driving_frame = driving_frame.cuda()
        
        kp_driving = kp_detector(driving_frame)
        kp_norm = normalize_kp(kp_source=kp_source, kp_driving=kp_driving,
                               kp_driving_initial=kp_detector(driving[:, :, 0]) if relative else None,
                               use_relative_movement=relative, use_relative_jacobian=relative,
                               adapt_movement_scale=adapt_movement_scale)
        
        out = generator(source, kp_source=kp_source, kp_driving=kp_norm)
        
        predictions.append(np.transpose(out['prediction'].data.cpu().numpy(), [0, 2, 3, 1])[0])
    
    print("\nSaving animated video...")
    imageio.mimsave(output_path, [img_as_ubyte(frame) for frame in predictions], fps=30)
    print(f"Animation saved to: {output_path}")

# Основная функция
if __name__ == "__main__":
    print("Loading model...")
    use_cpu = not torch.cuda.is_available()
    generator, kp_detector = load_checkpoints(args.config, args.checkpoint, cpu=use_cpu)
    
    print("Starting animation...")
    animate(args.input, args.driver, args.output, generator, kp_detector)
    print("Done!")