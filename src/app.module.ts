import { Module } from '@nestjs/common';
import { AnimationModule } from './animation/animation.module';

@Module({
  imports: [AnimationModule],
})
export class AppModule {}