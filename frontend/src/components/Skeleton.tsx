import { memo } from 'react';
import './Skeleton.css';

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
}

export const Skeleton = memo(function Skeleton({
  width = '100%',
  height = '1rem',
  borderRadius = '4px',
  className = '',
}: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius }}
      aria-hidden
    />
  );
});

export const SkeletonCard = memo(function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden>
      <Skeleton height="0" className="skeleton-card-image" borderRadius="6px" />
      <Skeleton width="75%" height="0.8rem" />
      <Skeleton width="50%" height="0.65rem" />
    </div>
  );
});

export const SkeletonRow = memo(function SkeletonRow() {
  return (
    <div className="skeleton-row" aria-hidden>
      <Skeleton width="40px" height="40px" borderRadius="4px" />
      <div className="skeleton-row-text">
        <Skeleton width="60%" height="0.75rem" />
        <Skeleton width="40%" height="0.6rem" />
      </div>
    </div>
  );
});

export const SkeletonHero = memo(function SkeletonHero() {
  return (
    <div className="skeleton-hero" aria-hidden>
      <Skeleton height="100%" borderRadius="0" />
    </div>
  );
});

export const SkeletonRail = memo(function SkeletonRail() {
  return (
    <div className="skeleton-rail" aria-hidden>
      <Skeleton width="120px" height="0.9rem" className="skeleton-rail-title" />
      <div className="skeleton-rail-items">
        {Array.from({ length: 10 }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
});

/** Skeleton fullscreen para Player/ReceiverPlayer (loading inicial). */
export const SkeletonPlayer = memo(function SkeletonPlayer() {
  return (
    <div className="skeleton-player" aria-busy="true" aria-label="Carregando player">
      <Skeleton width="80%" height="4rem" borderRadius="8px" className="skeleton-player-title" />
      <Skeleton width="60%" height="2rem" borderRadius="6px" className="skeleton-player-meta" />
    </div>
  );
});

/** Skeleton para cards de resultado de busca (cover, source, title, meta, actions). */
export const SkeletonSearchResultCard = memo(function SkeletonSearchResultCard() {
  return (
    <article className="skeleton-search-result-card" aria-hidden>
      <div className="skeleton-search-result-cover">
        <Skeleton height="100%" borderRadius="6px" />
      </div>
      <Skeleton width="4rem" height="0.75rem" borderRadius="4px" />
      <div className="skeleton-search-result-title">
        <Skeleton width="95%" height="0.9rem" borderRadius="4px" />
        <Skeleton width="70%" height="0.9rem" borderRadius="4px" />
      </div>
      <div className="skeleton-search-result-meta">
        <Skeleton width="2.5rem" height="0.75rem" borderRadius="4px" />
        <Skeleton width="2.5rem" height="0.75rem" borderRadius="4px" />
        <Skeleton width="2.5rem" height="0.75rem" borderRadius="4px" />
      </div>
      <div className="skeleton-search-result-actions">
        <Skeleton height="2rem" borderRadius="6px" />
        <Skeleton height="2rem" borderRadius="6px" />
      </div>
    </article>
  );
});
