import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { v4 as uuidv4 } from 'uuid';
import { firstValueFrom } from 'rxjs';

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
    private jobs: Map<string, Job> = new Map();

    constructor(private readonly httpService: HttpService) {
        this.storageServiceUrl = process.env.STORAGE_SERVICE_URL || 'http://storage-service:3002';
    }

    async createAnimationJob(imageUrl: string): Promise<{ jobId: string; status: string }> {
        const jobId = uuidv4();

        const job: Job = {
            id: jobId,
            status: 'pending',
            originalUrl: imageUrl,
            animatedUrl: null,
            createdAt: new Date(),
            completedAt: null,
        };

        this.jobs.set(jobId, job);

        // Запускаем процесс анимации асинхронно
        this.processAnimation(jobId, imageUrl);

        return {
            jobId,
            status: 'pending',
        };
    }

    async getJobStatus(jobId: string): Promise<Job> {
        const job = this.jobs.get(jobId);

        if (!job) {
            throw new HttpException('Job not found', HttpStatus.NOT_FOUND);
        }

        return job;
    }

    private async processAnimation(jobId: string, imageUrl: string): Promise<void> {
        try {
            const job = this.jobs.get(jobId);

            if (!job) {
                return;
            }

            // Обновляем статус задания
            job.status = 'processing';
            this.jobs.set(jobId, job);

            // Загружаем изображение из URL
            const downloadResponse = await firstValueFrom(
                this.httpService.post(`${this.storageServiceUrl}/download`, { url: imageUrl })
            );

            const localImagePath = downloadResponse.data.path;

            console.log(`Starting animation for job ${jobId} with image: ${localImagePath}`);

            // Запускаем процесс анимации с использованием TPSMM
            await this.animateWithNeuralNetwork(localImagePath);

            // Имя файла с результатом анимации
            const animatedFilePath = `${localImagePath}.mp4`;
            const fileName = `animated_${jobId}.mp4`;

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
            this.jobs.set(jobId, job);

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

            const job = this.jobs.get(jobId);
            if (job) {
                job.status = 'failed';
                job.completedAt = new Date();
                this.jobs.set(jobId, job);
            }
        }
    }


    private async animateWithNeuralNetwork(imagePath: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const { spawn } = require('child_process');

            console.log(`Starting animation for ${imagePath}`);

            const outputPath = `${imagePath}.mp4`;

            const pythonProcess = spawn('python', [
                '/app/models/animate.py',
                '--input', imagePath,
                '--output', outputPath,
                '--driver', '/app/models/driving_video.mp4',
                '--config', '/app/models/Thin-Plate-Spline-Motion-Model/config/vox-256.yaml',
                '--checkpoint', '/app/models/Thin-Plate-Spline-Motion-Model/checkpoints/vox.pth.tar'
            ]);

            pythonProcess.stdout.on('data', (data) => {
                console.log(`Animation process: ${data}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                console.error(`Animation process error: ${data}`);
            });

            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    console.log(`Animation completed successfully for ${imagePath}`);
                    resolve();
                } else {
                    console.error(`Animation process exited with code ${code}`);
                    reject(new Error(`Animation failed with code ${code}`));
                }
            });
        });
    }
}