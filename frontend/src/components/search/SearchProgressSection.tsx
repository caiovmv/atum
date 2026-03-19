import { IoCheckmarkCircle, IoCloseCircleOutline } from 'react-icons/io5';
import { INDEXER_ORDER, indexerLabel } from '../../utils/searchStorage';

interface SearchProgressSectionProps {
  indexerProgress: Record<string, 'pending' | 'loading' | 'done' | 'error'>;
  indexerCounts: Record<string, number>;
}

export function SearchProgressSection({ indexerProgress, indexerCounts }: SearchProgressSectionProps) {
  const keys = Object.keys(indexerProgress);
  if (keys.length === 0) return null;

  const doneCount = Object.values(indexerProgress).filter((s) => s === 'done' || s === 'error').length;
  const progressPercent = (doneCount / keys.length) * 100;

  return (
    <div className="search-progress-wrap search-progress-wrap--compact" role="status" aria-live="polite" aria-label="Progresso da busca por indexador">
      <div className="search-progress-bar-wrap">
        <div
          className="search-progress-bar-fill"
          role="progressbar"
          aria-valuenow={Math.round(progressPercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${doneCount} de ${keys.length} indexadores concluídos`}
          style={{ width: `${progressPercent}%` }}
        />
        <span className="search-progress-bar-label">
          {doneCount} / {keys.length}
        </span>
      </div>
      <div className="search-progress-indexers">
        {INDEXER_ORDER.filter((key) => key in indexerProgress).map((key) => {
          const status = indexerProgress[key];
          const count = indexerCounts[key] ?? 0;
          return (
            <span
              key={key}
              className={`search-progress-indexer search-progress-indexer--${status}`}
              title={status === 'loading' ? 'Buscando…' : status === 'done' ? `${count} resultado(s)` : 'Falha'}
            >
              {status === 'loading' && <span className="search-progress-spinner" aria-hidden />}
              {status === 'done' && <IoCheckmarkCircle className="search-progress-icon" aria-hidden />}
              {status === 'error' && <IoCloseCircleOutline className="search-progress-icon search-progress-icon--error" aria-hidden />}
              <span className="search-progress-indexer-name">{indexerLabel(key)}</span>
              {status === 'done' && count >= 0 && <span className="search-progress-count">{count}</span>}
            </span>
          );
        })}
      </div>
    </div>
  );
}
