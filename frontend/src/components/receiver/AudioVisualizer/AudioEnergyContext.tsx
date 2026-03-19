import { createContext, useContext, type ReactNode } from 'react';
import type { AudioEnergy } from '../../../audio/audioEnergy';

type GetAudioEnergy = () => AudioEnergy;

const AudioEnergyCtx = createContext<GetAudioEnergy | null>(null);

export function useAudioEnergyContext(): GetAudioEnergy {
  const getter = useContext(AudioEnergyCtx);
  if (!getter) {
    return () => ({ bass: 0, mid: 0, treble: 0 });
  }
  return getter;
}

interface AudioEnergyProviderProps {
  children: ReactNode;
  getAudioEnergy: GetAudioEnergy;
}

export function AudioEnergyProvider({
  children,
  getAudioEnergy,
}: AudioEnergyProviderProps) {
  return (
    <AudioEnergyCtx.Provider value={getAudioEnergy}>
      {children}
    </AudioEnergyCtx.Provider>
  );
}
