import { Controller, Post, Get, Body, Param } from '@nestjs/common';
import { AnimationService, Job } from './animation.service';
import { MessagePattern, Payload } from '@nestjs/microservices';

@Controller()
export class AnimationController {
  constructor(private readonly animationService: AnimationService) {}

  // Оставляем REST endpoint для обратной совместимости
  @Post('process')
  async processImage(@Body() body: { imageUrl: string }) {
    return this.animationService.createAnimationJob(body.imageUrl);
  }

  // Добавляем обработчик сообщений из RabbitMQ
  @MessagePattern('create_animation')
  async handleAnimationRequest(@Payload() data: { jobId: string, imageUrl: string }) {
    return this.animationService.createAnimationJobWithId(data.jobId, data.imageUrl);
  }

  @Get('status/:jobId')
  async getJobStatus(@Param('jobId') jobId: string): Promise<Job> {
    return this.animationService.getJobStatus(jobId);
  }
}