import { useState, useEffect, useRef, useCallback } from 'react';

const BATCH_SIZE = 30;

/**
 * Progressively renders items in batches as the user scrolls.
 * Uses IntersectionObserver on a sentinel element.
 */
export function useInfiniteRender<T>(items: T[], batchSize = BATCH_SIZE) {
  const [visibleCount, setVisibleCount] = useState(batchSize);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVisibleCount(batchSize);
  }, [items, batchSize]);

  const loadMore = useCallback(() => {
    setVisibleCount(prev => Math.min(prev + batchSize, items.length));
  }, [batchSize, items.length]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: '200px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  const visible = items.slice(0, visibleCount);
  const hasMore = visibleCount < items.length;

  return { visible, hasMore, sentinelRef };
}
