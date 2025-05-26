FROM python:3.8

# Установка Node.js (используем совместимую версию)
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs git

# Установка npm (указываем совместимую версию)
RUN npm install -g npm@9

WORKDIR /app

# Клонирование репозитория модели TPSMM
RUN mkdir -p /app/models
RUN git clone https://github.com/yoyo-nb/Thin-Plate-Spline-Motion-Model /app/models/Thin-Plate-Spline-Motion-Model

# Установка зависимостей Python для модели с более новыми версиями PyTorch
WORKDIR /app/models/Thin-Plate-Spline-Motion-Model
# Используем более новую версию PyTorch
RUN pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1
RUN pip install pyyaml==5.4.1 scikit-image==0.17.2 imageio==2.9.0 imageio-ffmpeg==0.4.5 opencv-python==4.5.1.48 matplotlib==3.3.4 pandas==1.2.2

# Создание директории для контрольных точек
RUN mkdir -p checkpoints

# Скачивание предобученной модели
RUN apt-get install -y wget
RUN wget --no-check-certificate 'https://drive.google.com/uc?export=download&id=1qf596VuU-oONb-FW8w2UjHHkTzU8SMnk' -O checkpoints/vox.pth.tar || \
    wget --no-check-certificate 'https://github.com/yoyo-nb/Thin-Plate-Spline-Motion-Model/releases/download/v1.0.0/vox.pth.tar' -O checkpoints/vox.pth.tar

# Скачивание видео-драйвера для анимации
WORKDIR /app/models
RUN wget --no-check-certificate 'https://github.com/AliaksandrSiarohin/first-order-model/raw/master/sup-mat/driving.mp4' -O driving_video.mp4

# Копирование скрипта анимации
COPY models/animate.py /app/models/

# Возвращение в корневую директорию
WORKDIR /app

# Копирование и установка Node.js приложения
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3001

CMD ["node", "dist/main"]