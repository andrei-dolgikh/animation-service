FROM python:3.8

# Установка Node.js (используем совместимую версию)
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs git wget

# Установка npm (указываем совместимую версию)
RUN npm install -g npm@9

WORKDIR /app

# Создание директории для моделей
RUN mkdir -p /app/models

# Клонирование репозитория TPSMM
RUN git clone https://github.com/yoyo-nb/Thin-Plate-Spline-Motion-Model /app/models/Thin-Plate-Spline-Motion-Model

# Установка зависимостей Python для моделей
RUN pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1
RUN pip install pyyaml==5.4.1 scikit-image==0.17.2 imageio==2.9.0 imageio-ffmpeg==0.4.5 opencv-python==4.5.1.48 matplotlib==3.3.4 pandas==1.2.2 pillow==9.3.0 gdown==4.7.1

# Создание директории для контрольных точек TPSMM
WORKDIR /app/models/Thin-Plate-Spline-Motion-Model
RUN mkdir -p checkpoints

# Клонирование репозитория FOMM
RUN git clone https://github.com/AliaksandrSiarohin/first-order-model /app/models/first-order-model

# Скачивание видео-драйвера для анимации
WORKDIR /app/models
RUN wget --no-check-certificate 'https://github.com/AliaksandrSiarohin/first-order-model/raw/master/sup-mat/driving.mp4' -O driving_video.mp4 || \
    wget --no-check-certificate 'https://github.com/AliaksandrSiarohin/first-order-model/raw/master/sup-mat/vox-teaser.mp4' -O driving_video.mp4 || \
    echo "Could not download driving video, will need to be provided manually"

# Копирование скриптов анимации
COPY models/animate_fom.py /app/models/
COPY models/simple_animate.py /app/models/

# Установка зависимостей для FOMM
WORKDIR /app/models/first-order-model
RUN pip install -r requirements.txt || pip install face-alignment==1.3.5 pyyaml==5.4.1 scikit-image==0.17.2 imageio==2.9.0 imageio-ffmpeg==0.4.5 opencv-python==4.5.1.48

# Копирование исходного кода приложения
WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3001
CMD ["npm", "run", "start:prod"]