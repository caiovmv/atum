import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCrossfade } from '../useCrossfade';
import type { AudioEngine } from '../../audio/audioEngine';

function createMockEngine(): AudioEngine {
  const gainNode = {
    gain: {
      value: 1,
      cancelScheduledValues: vi.fn(),
      setValueAtTime: vi.fn(),
      exponentialRampToValueAtTime: vi.fn(),
    },
  };
  return {
    ctx: { currentTime: 0, state: 'running' } as unknown as AudioContext,
    volumeGain: gainNode as unknown as GainNode,
  } as unknown as AudioEngine;
}

describe('useCrossfade', () => {
  let engine: AudioEngine;

  beforeEach(() => {
    engine = createMockEngine();
  });

  it('does not fade on initial render', () => {
    renderHook(() => useCrossfade(engine, '/stream/1', 80, false));
    const gain = engine.volumeGain.gain as unknown as { exponentialRampToValueAtTime: ReturnType<typeof vi.fn> };
    expect(gain.exponentialRampToValueAtTime).not.toHaveBeenCalled();
  });

  it('fades out when streamUrl changes', () => {
    const { rerender } = renderHook(
      ({ url }) => useCrossfade(engine, url, 80, false),
      { initialProps: { url: '/stream/1' } },
    );
    rerender({ url: '/stream/2' });
    const gain = engine.volumeGain.gain as unknown as {
      cancelScheduledValues: ReturnType<typeof vi.fn>;
      setValueAtTime: ReturnType<typeof vi.fn>;
      exponentialRampToValueAtTime: ReturnType<typeof vi.fn>;
    };
    expect(gain.cancelScheduledValues).toHaveBeenCalled();
    expect(gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.001, expect.any(Number));
  });

  it('fades in when isPlaying becomes true after URL change', () => {
    const { rerender } = renderHook(
      ({ url, playing }) => useCrossfade(engine, url, 80, playing),
      { initialProps: { url: '/stream/1', playing: false } },
    );
    rerender({ url: '/stream/2', playing: false });
    rerender({ url: '/stream/2', playing: true });
    const gain = engine.volumeGain.gain as unknown as {
      exponentialRampToValueAtTime: ReturnType<typeof vi.fn>;
    };
    const calls = gain.exponentialRampToValueAtTime.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[0]).toBeCloseTo(0.8, 1);
  });
});
