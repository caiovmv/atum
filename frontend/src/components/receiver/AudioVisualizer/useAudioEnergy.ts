import { useRef, useEffect, useCallback } from 'react';
import { extractAudioEnergy, type AudioEnergy } from '../../../audio/audioEnergy';

const DEFAULT_ENERGY: AudioEnergy = { bass: 0, mid: 0, treble: 0 };

/** Suavização: ataque rápido (subida), decay mais lento (descida) */
const ATTACK = 0.55;
const DECAY = 0.18;

/**
 * Hook que fornece getAudioEnergy() para o loop de desenho.
 * Atualiza um ref a cada frame — não causa re-renders.
 * Aplica suavização com ataque rápido para resposta mais perceptível.
 */
export function useAudioEnergy(analyser: AnalyserNode | null) {
  const energyRef = useRef<AudioEnergy>(DEFAULT_ENERGY);
  const smoothedRef = useRef<AudioEnergy>(DEFAULT_ENERGY);
  const freqBufRef = useRef<Uint8Array | null>(null);

  useEffect(() => {
    if (!analyser) {
      energyRef.current = DEFAULT_ENERGY;
      smoothedRef.current = DEFAULT_ENERGY;
      return;
    }

    const binCount = analyser.frequencyBinCount;
    if (!freqBufRef.current || freqBufRef.current.length !== binCount) {
      freqBufRef.current = new Uint8Array(binCount);
    }

    let raf = 0;
    const tick = () => {
      const buf = freqBufRef.current;
      if (buf) {
        const raw = extractAudioEnergy(analyser, buf);
        const prev = smoothedRef.current;
        const alphaBass = raw.bass > prev.bass ? ATTACK : DECAY;
        const alphaMid = raw.mid > prev.mid ? ATTACK : DECAY;
        const alphaTreble = raw.treble > prev.treble ? ATTACK : DECAY;
        smoothedRef.current = {
          bass: prev.bass + (raw.bass - prev.bass) * alphaBass,
          mid: prev.mid + (raw.mid - prev.mid) * alphaMid,
          treble: prev.treble + (raw.treble - prev.treble) * alphaTreble,
        };
        energyRef.current = smoothedRef.current;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(raf);
  }, [analyser]);

  const getAudioEnergy = useCallback((): AudioEnergy => {
    return energyRef.current;
  }, []);

  return getAudioEnergy;
}
