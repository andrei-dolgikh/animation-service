import { Controller, Post, Get, Body, Param } from '@nestjs/common';
import { AnimationService, Job } from './animation.service';

@Controller()
export class AnimationController {
  constructor(private readonly animationService: AnimationService) {}

  @Post('process')
  async processImage(@Body() body: { imageUrl: string }) {
    return this.animationService.createAnimationJob(body.imageUrl);
  }

  @Get('status/:jobId')
  async getJobStatus(@Param('jobId') jobId: string): Promise<Job>  {
    return this.animationService.getJobStatus(jobId);
  }
}