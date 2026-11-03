import React from 'react';
import { Composition } from 'remotion';
import { TraziaPromo } from './Main';
import { FPS, TOTAL } from './timeline';

export const Root: React.FC = () => (
  <Composition id="TraziaPromo" component={TraziaPromo} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} defaultProps={{ bgm: true }} />
);
