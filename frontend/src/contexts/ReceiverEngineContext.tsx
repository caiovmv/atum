import { createContext, useContext, type ReactNode } from 'react';
import type { AudioEngine } from '../audio/audioEngine';

interface ReceiverEngineContextValue {
  engine: AudioEngine | null;
}

const ReceiverEngineCtx = createContext<ReceiverEngineContextValue | null>(null);

export function useReceiverEngine(): AudioEngine | null {
  const ctx = useContext(ReceiverEngineCtx);
  return ctx?.engine ?? null;
}

interface ReceiverEngineProviderProps {
  children: ReactNode;
  engine: AudioEngine | null;
}

export function ReceiverEngineProvider({
  children,
  engine,
}: ReceiverEngineProviderProps) {
  const value: ReceiverEngineContextValue = { engine };
  return (
    <ReceiverEngineCtx.Provider value={value}>
      {children}
    </ReceiverEngineCtx.Provider>
  );
}
