import { createContext, useContext } from 'react';
import { useCurrentFrame } from 'remotion';

// Las escenas se escriben en fotogramas absolutos de timeline.ts. Dentro de una <Sequence from={x}>
// el fotograma es relativo, así que cada escena publica su desplazamiento y useF() lo suma.
export const FrameOffset = createContext(0);
export const useF = () => useCurrentFrame() + useContext(FrameOffset);
