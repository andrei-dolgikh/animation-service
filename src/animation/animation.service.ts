import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { v4 as uuidv4 } from 'uuid';
import { firstValueFrom } from 'rxjs';
import * as ioredis from 'ioredis';

export interface Job {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    originalUrl: string;
    animatedUrl: string | null;
    createdAt: Date;
    completedAt: Date | null;
}

@Injectable()
export class AnimationService {
    private readonly storageServiceUrl: string;
    private readonly redis: ioredis.Redis;

    constructor(private readonly httpService: HttpService) {
        this.storageServiceUrl = process.env.STORAGE_SERVICE_URL || 'http://storage-service:3002';
        this.redis = new ioredis.Redis({
            host: process.env.REDIS_HOST || 'redis',
            port: parseInt(process.env.REDIS_PORT || '6379'),
        });
    }

    // Существующий метод для REST API
    async createAnimationJob(imageUrl: string): Promise<{ jobId: string; status: string }> {
        const jobId = uuidv4();
        return this.createAnimationJobWithId(jobId, imageUrl);
    }

    // Новый метод для обработки сообщений из RabbitMQ
    async createAnimationJobWithId(jobId: string, imageUrl: string): Promise<{ jobId: string; status: string }> {
        const job: Job = {
            id: jobId,
            status: 'pending',
            originalUrl: imageUrl,
            animatedUrl: null,
            createdAt: new Date(),
            completedAt: null,
        };

        // Сохраняем состояние задания в Redis
        await this.saveJob(job);

        // Запускаем процесс анимации асинхронно
        this.processAnimation(jobId, imageUrl);

        return {
            jobId,
            status: 'pending',
        };
    }

    async getJobStatus(jobId: string): Promise<Job> {
        // Получаем задание из Redis
        const jobJson = await this.redis.get(`job:${jobId}`);
        
        if (!jobJson) {
            throw new HttpException('Job not found', HttpStatus.NOT_FOUND);
        }
        
        return JSON.parse(jobJson);
    }

    private async saveJob(job: Job): Promise<void> {
        await this.redis.set(`job:${job.id}`, JSON.stringify(job));
    }

    private async processAnimation(jobId: string, imageUrl: string): Promise<void> {
        try {
            // Получаем задание из Redis
            const jobJson = await this.redis.get(`job:${jobId}`);
            if (!jobJson) {
                console.error(`Job ${jobId} not found in Redis`);
                return;
            }
            
            const job: Job = JSON.parse(jobJson);
            
            // Обновляем статус задания
            job.status = 'processing';
            await this.saveJob(job);
            
            console.log(`Processing animation for job ${jobId} with image: ${imageUrl}`);
            
            // Загружаем изображение из URL
            const downloadResponse = await firstValueFrom(
                this.httpService.post(`${this.storageServiceUrl}/download`, { url: imageUrl })
            );
            
            const localImagePath = downloadResponse.data.path;
            
            console.log(`Starting animation for job ${jobId} with image: ${localImagePath}`);
            
            // Запускаем процесс анимации
            await this.animateWithNeuralNetwork(localImagePath);
            
            // Имя файла с результатом анимации
            const animatedFilePath = `${localImagePath}.gif`;
            const fileName = `animated_${jobId}.gif`;
            
            // После обработки загружаем результат в хранилище
            const uploadResponse = await firstValueFrom(
                this.httpService.post(`${this.storageServiceUrl}/upload`, { 
                    filePath: animatedFilePath,
                    fileName: fileName
                })
            );
            
            // Обновляем задание с URL анимированного изображения
            job.status = 'completed';
            job.animatedUrl = uploadResponse.data.url;
            job.completedAt = new Date();
            await this.saveJob(job);
            
            console.log(`Animation job ${jobId} completed successfully. Result: ${job.animatedUrl}`);
            
            // Удаляем временные файлы
            try {
                const fs = require('fs');
                fs.unlinkSync(localImagePath);
                fs.unlinkSync(animatedFilePath);
                console.log(`Temporary files for job ${jobId} cleaned up`);
            } catch (cleanupError) {
                console.error(`Error cleaning up temporary files for job ${jobId}:`, cleanupError);
            }
            
        } catch (error) {
            console.error(`Animation processing error for job ${jobId}:`, error);
            
            // Получаем задание из Redis и обновляем статус
            const jobJson = await this.redis.get(`job:${jobId}`);
            if (jobJson) {
                const job: Job = JSON.parse(jobJson);
                job.status = 'failed';
                job.completedAt = new Date();
                await this.saveJob(job);
            }
        }
    }


  private async animateWithNeuralNetwork(imagePath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const { spawn } = require('child_process');

      console.log(`Starting animation for ${imagePath}`);

      const outputPath = `${imagePath}.gif`;

      // Попробуем сначала TPSMM
      const pythonProcess = spawn('python', [
        '/app/models/animate.py',
        '--input', imagePath,
        '--output', outputPath,
        '--driver', '/app/models/driving_video.mp4',
        '--config', '/app/models/Thin-Plate-Spline-Motion-Model/config/vox-256.yaml',
        '--checkpoint', '/app/models/Thin-Plate-Spline-Motion-Model/checkpoints/vox.pth.tar'
      ]);

      let stdoutData = '';
      let stderrData = '';

      pythonProcess.stdout.on('data', (data) => {
        const message = data.toString();
        stdoutData += message;
        console.log(`Animation process: ${message}`);
      });

      pythonProcess.stderr.on('data', (data) => {
        const message = data.toString();
        stderrData += message;
        console.error(`Animation process error: ${message}`);
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          console.log(`Animation completed successfully for ${imagePath}`);
          resolve();
        } else {
          console.error(`TPSMM animation failed with code ${code}. Trying fallback model...`);

          // Если TPSMM не сработал, используем FOMM как запасной вариант
          this.animateWithFallbackModel(imagePath, outputPath)
            .then(resolve)
            .catch(reject);
        }
      });
    });
  }

  private async animateWithFallbackModel(imagePath: string, outputPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const { spawn } = require('child_process');

      console.log(`Starting fallback animation for ${imagePath}`);

      const pythonProcess = spawn('python', [
        '/app/models/animate_fom.py',
        '--input', imagePath,
        '--output', outputPath,
        '--driver', '/app/models/driving_video.mp4'
      ]);

      pythonProcess.stdout.on('data', (data) => {
        console.log(`Fallback animation process: ${data}`);
      });

      pythonProcess.stderr.on('data', (data) => {
        console.error(`Fallback animation process error: ${data}`);
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          console.log(`Fallback animation completed successfully for ${imagePath}`);
          resolve();
        } else {
          console.error(`Fallback animation failed with code ${code}`);
          reject(new Error(`All animation methods failed for ${imagePath}`));
        }
      });
    });
  }
}