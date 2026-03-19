import { EmptyState } from '../EmptyState';
import { SkeletonRow } from '../Skeleton';
import type { Feed } from '../../types/feeds';

interface FeedsListProps {
  feeds: Feed[];
  loading: boolean;
  onRemove: (id: number) => void;
}

export function FeedsList({ feeds, loading, onRemove }: FeedsListProps) {
  return (
    <section className="atum-feeds-list-section" aria-labelledby="feeds-list-heading">
      <h2 id="feeds-list-heading" className="atum-feeds-section-title">Feeds inscritos</h2>
      {loading ? (
        <div className="atum-feeds-skeleton" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => <SkeletonRow key={i} />)}
        </div>
      ) : feeds.length === 0 ? (
        <EmptyState
          title="Nenhum feed"
          description="Adicione uma URL de feed RSS acima para receber novidades."
        />
      ) : (
        <ul className="atum-feeds-ul">
          {feeds.map((feed) => (
            <li key={feed.id} className="atum-feeds-item">
              <div className="atum-feeds-item-info">
                <span className="atum-feeds-item-url">{feed.url}</span>
                {feed.title && <span> — {feed.title}</span>}
                <span className="atum-feeds-item-badge">{(feed.content_type || 'music')}</span>
              </div>
              <button
                type="button"
                className="atum-btn atum-btn-small"
                onClick={() => onRemove(feed.id)}
                aria-label={`Remover feed ${feed.url}`}
              >
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
