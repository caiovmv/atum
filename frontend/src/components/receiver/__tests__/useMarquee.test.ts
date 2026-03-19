import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMarquee } from '../../../hooks/useMarquee';

let observeCallback: ResizeObserverCallback;
let mockDisconnect: () => void;

beforeEach(() => {
  mockDisconnect = vi.fn() as unknown as () => void;
  vi.stubGlobal('ResizeObserver', class {
    constructor(cb: ResizeObserverCallback) { observeCallback = cb; }
    observe() {}
    unobserve() {}
    disconnect() { mockDisconnect(); }
  });
});

function makeRef(scrollWidth: number, clientWidth: number) {
  return {
    current: { scrollWidth, clientWidth } as unknown as HTMLElement,
  };
}

describe('useMarquee', () => {
  it('returns false when text fits', () => {
    const ref = makeRef(100, 200);
    const { result } = renderHook(() => useMarquee(ref, 'short'));
    expect(result.current).toBe(false);
  });

  it('returns true when text overflows', () => {
    const ref = makeRef(300, 200);
    const { result } = renderHook(() => useMarquee(ref, 'very long title'));
    expect(result.current).toBe(true);
  });

  it('returns false when ref is null', () => {
    const ref = { current: null };
    const { result } = renderHook(() => useMarquee(ref, 'text'));
    expect(result.current).toBe(false);
  });

  it('disconnects observer on unmount', () => {
    const ref = makeRef(100, 200);
    const { unmount } = renderHook(() => useMarquee(ref, 'text'));
    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('updates when ResizeObserver fires', () => {
    const el = { scrollWidth: 100, clientWidth: 200 } as unknown as HTMLElement;
    const ref = { current: el };
    const { result } = renderHook(() => useMarquee(ref, 'text'));
    expect(result.current).toBe(false);

    act(() => {
      (el as unknown as { scrollWidth: number }).scrollWidth = 300;
      observeCallback([] as unknown as ResizeObserverEntry[], {} as ResizeObserver);
    });
    expect(result.current).toBe(true);
  });
});
