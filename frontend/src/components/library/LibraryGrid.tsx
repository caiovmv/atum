import { IoPlay, IoInformationCircleOutline } from 'react-icons/io5';
import { MediaCard } from '../MediaCard';
import { CoverImage } from '../CoverImage';
import { EmptyState } from '../EmptyState';
import { SkeletonCard } from '../Skeleton';
import { statusLabel } from '../../utils/format';
import { getFormatBadge } from '../../utils/getFormatBadge';
import type { LibraryItem, ContentType } from '../../types/library';
import type { ContentTypeTab, ViewMode } from '../../hooks/useLibrary';

function toContentType(ct: string | undefined): ContentType {
  return ct === 'movies' || ct === 'tv' ? ct : 'music';
}

function ctLabel(ct: string): string {
  return ct === 'movies' ? 'Filme' : ct === 'tv' ? 'Série' : ct === 'concerts' ? 'Concerto' : 'Música';
}

interface LibraryGridProps {
  contentType: ContentTypeTab;
  viewMode: ViewMode;
  loading: boolean;
  fetchError: string | null;
  visibleItems: LibraryItem[];
  hasMore: boolean;
  sentinelRef: React.RefObject<HTMLDivElement | null>;
  onRetry: () => void;
  onPlay: (item: LibraryItem) => void;
  onCoverRefresh: (item: LibraryItem) => void;
  onEdit: (item: LibraryItem) => void;
  onInfoClick: (item: LibraryItem | null) => void;
}

export function LibraryGrid({
  contentType,
  viewMode,
  loading,
  fetchError,
  visibleItems,
  hasMore,
  sentinelRef,
  onRetry,
  onPlay,
  onCoverRefresh,
  onEdit,
  onInfoClick,
}: LibraryGridProps) {
  const isVideo = contentType === 'movies' || contentType === 'tv';
  const isMusic = contentType === 'music' || contentType === 'concerts';
  if (loading) {
    return (
      <div className="library-skeleton-grid" aria-busy="true">
        {Array.from({ length: 12 }, (_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="library-fetch-error" role="alert">
        <p>{fetchError}</p>
        <button type="button" className="atum-btn atum-btn-primary" onClick={onRetry}>
          Tentar novamente
        </button>
      </div>
    );
  }

  if (visibleItems.length === 0) {
    return (
      <EmptyState
        title="Nenhum item na biblioteca"
        description="Conclua downloads ou importe pastas para ver aqui."
        action={
          <button type="button" className="atum-btn atum-btn-primary" onClick={onRetry}>
            Tentar novamente
          </button>
        }
      />
    );
  }

  const InfoButton = ({ item }: { item: LibraryItem }) => (
    <button
      type="button"
      className="atum-library-info-btn"
      onClick={(e) => {
        e.stopPropagation();
        onInfoClick(item);
      }}
      title="Ver detalhes"
      aria-label={`Ver detalhes de ${item.name || 'item'}`}
    >
      <IoInformationCircleOutline size={20} />
    </button>
  );

  if (viewMode === 'list') {
    return (
      <div className="atum-library-list">
        {visibleItems.map((item) => (
          <div
            key={`${item.source || 'download'}-${item.id}`}
            className="atum-library-list-row"
          >
            <div className="atum-library-list-cover">
              <CoverImage
                contentType={toContentType(item.content_type)}
                title={item.name || ''}
                downloadId={item.source === 'import' ? undefined : item.id}
                importId={item.source === 'import' ? item.id : undefined}
                size="thumb"
              />
            </div>
            <div className="atum-library-list-body">
              <span className="atum-library-list-title">{item.name || '—'}</span>
              <span className="atum-library-list-meta">
                {[item.artist, item.album, item.year ? String(item.year) : '', ctLabel(item.content_type || 'music')]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            </div>
            <div className="atum-library-list-actions">
              {item.content_path && (
                <button
                  type="button"
                  className="atum-btn atum-btn-primary"
                  onClick={() => onPlay(item)}
                  aria-label={`Reproduzir ${item.name || 'item'}`}
                >
                  <IoPlay size={18} />
                </button>
              )}
              <InfoButton item={item} />
            </div>
          </div>
        ))}
        {hasMore && <div ref={sentinelRef} className="library-scroll-sentinel" />}
      </div>
    );
  }

  return (
    <div className={`atum-library-grid${isVideo ? ' atum-library-grid--videos' : ''}`}>
      {visibleItems.map((item) => (
        <MediaCard
          key={`${item.source || 'download'}-${item.id}`}
          cover={{
            contentType: toContentType(item.content_type),
            title: item.name || '',
            downloadId: item.source === 'import' ? undefined : item.id,
            importId: item.source === 'import' ? item.id : undefined,
          }}
          coverShape={isMusic ? 'square' : 'poster'}
          badge={getFormatBadge(item)}
          title={item.name || '—'}
          meta={[
            item.year ? String(item.year) : '',
            item.artist && isMusic ? item.artist : '',
            item.album && isMusic ? item.album : '',
            ctLabel(item.content_type || 'music'),
            ...((item.tags || []).length > 0 ? [`🏷 ${(item.tags || []).join(', ')}`] : []),
          ].filter(Boolean)}
          showSeLe={false}
          overlay={
            item.source !== 'import' && item.status && item.status !== 'completed'
              ? {
                  type: item.progress != null ? 'progress' : 'status',
                  label: statusLabel(item.status),
                  percent: item.progress,
                }
              : undefined
          }
          primaryAction={
            item.content_path ? (
              <button
                type="button"
                className="media-card-play-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onPlay(item);
                }}
                aria-label={`Reproduzir ${item.name || 'item'}`}
              >
                <IoPlay size={24} />
              </button>
            ) : undefined
          }
          coverCorner={<InfoButton item={item} />}
          actions={
            <div className="atum-library-card-actions-inner">
              {item.content_path && (
                <button
                  type="button"
                  className="atum-btn atum-btn-primary atum-library-edit-play-btn"
                  onClick={() => onPlay(item)}
                >
                  Reproduzir
                </button>
              )}
              <button
                type="button"
                className="atum-btn"
                onClick={() => onCoverRefresh(item)}
                title="Buscar capa"
                aria-label={`Buscar capa de ${item.name || 'item'}`}
              >
                Capa
              </button>
              {item.source === 'import' && (
                <button
                  type="button"
                  className="atum-btn"
                  onClick={() => onEdit(item)}
                  title="Editar metadados"
                  aria-label={`Editar metadados de ${item.name || 'item'}`}
                >
                  Editar
                </button>
              )}
            </div>
          }
        />
      ))}
      {hasMore && <div ref={sentinelRef} className="library-scroll-sentinel" />}
    </div>
  );
}
