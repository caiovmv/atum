import './SearchResultCardSkeleton.css';

export function SearchResultCardSkeleton() {
  return (
    <article className="search-result-card-skeleton" aria-hidden>
      <div className="search-result-card-skeleton-cover" />
      <div className="search-result-card-skeleton-source" />
      <div className="search-result-card-skeleton-title">
        <span />
        <span />
      </div>
      <div className="search-result-card-skeleton-meta">
        <span />
        <span />
        <span />
      </div>
      <div className="search-result-card-skeleton-actions">
        <span />
        <span />
      </div>
    </article>
  );
}
