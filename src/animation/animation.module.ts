import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { AnimationController } from './animation.controller';
import { AnimationService } from './animation.service';

@Module({
  imports: [HttpModule],
  controllers: [AnimationController],
  providers: [AnimationService],
})
export class AnimationModule {}