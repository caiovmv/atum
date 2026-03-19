import { useState, useEffect, type RefObject } from 'react';

export function useMarquee(ref: RefObject<HTMLElement | null>, text: string): boolean {
  const [overflow, setOverflow] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setOverflow(el.scrollWidth > el.clientWidth + 2);
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, text]);
  return overflow;
}
