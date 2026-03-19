import { useRef, useEffect } from 'react';
import type { AudioEngine } from '../audio/audioEngine';

const FADE_DURATION = 0.6;

/**
 * Crossfade hook: fades volume out when streamUrl changes,
 * then fades back in when new audio starts playing.
 * Uses Web Audio API's exponentialRampToValueAtTime for smooth transitions.
 */
export function useCrossfade(
  engine: AudioEngine | null,
  streamUrl: string,
  volume: number,
  isPlaying: boolean,
) {
  const prevUrlRef = useRef(streamUrl);
  const fadingRef = useRef(false);

  useEffect(() => {
    if (!engine || streamUrl === prevUrlRef.current) return;
    prevUrlRef.current = streamUrl;

    const gain = engine.volumeGain;
    const ctx = engine.ctx;
    if (ctx.state === 'closed') return;

    fadingRef.current = true;
    const now = ctx.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + FADE_DURATION);
  }, [engine, streamUrl]);

  useEffect(() => {
    if (!engine || !fadingRef.current || !isPlaying) return;

    fadingRef.current = false;
    const gain = engine.volumeGain;
    const ctx = engine.ctx;
    if (ctx.state === 'closed') return;

    const targetVol = Math.max(0.001, volume / 100);
    const now = ctx.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(targetVol, now + FADE_DURATION);
  }, [engine, isPlaying, volume]);
}
