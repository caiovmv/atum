import { useNavigate } from 'react-router-dom';
import { IoAdd } from 'react-icons/io5';
import { MediaCard } from '../MediaCard';
import { SkeletonSearchResultCard } from '../Skeleton';
import { statusLabel } from '../../utils/format';
import { indexerLabel, normalizeMagnet } from '../../utils/searchStorage';
import type { SearchResult } from '../../types/search';

const PAGE_SIZE = 20;

interface PageResult {
  r: SearchResult;
  originalIndex: number;
}

interface SearchResultsGridProps {
  loading: boolean;
  resultsLength: number;
  pageResults: PageResult[];
  filteredResultsLength: number;
  page: number;
  totalPages: number;
  setPage: (v: number | ((p: number) => number)) => void;
  contentType: 'music' | 'movies' | 'tv';
  sortBy: 'seeders' | 'size';
  query: string;
  start: number;
  downloads: Array<{ id?: string | number; magnet?: string; status: string; progress?: number }>;
  onOpenFilesModal: (r: SearchResult) => void;
  onOpenAddModal: (r: SearchResult) => void;
}

export function SearchResultsGrid({
  loading,
  resultsLength,
  pageResults,
  filteredResultsLength,
  page,
  totalPages,
  setPage,
  contentType,
  sortBy,
  query,
  start,
  downloads,
  onOpenFilesModal,
  onOpenAddModal,
}: SearchResultsGridProps) {
  const navigate = useNavigate();

  return (
    <>
      <div className="results-grid">
        {loading && resultsLength === 0
          ? Array.from({ length: 10 }, (_, i) => <SkeletonSearchResultCard key={`skeleton-${i}`} />)
          : pageResults.map(({ r, originalIndex }, idx) => {
            const match = r.magnet ? downloads.find((d) => normalizeMagnet(d.magnet) === normalizeMagnet(r.magnet!)) : null;
            const overlay = match
              ? {
                  type: (match.progress != null ? 'progress' : 'status') as 'progress' | 'status',
                  label: statusLabel(match.status),
                  percent: match.progress,
                }
              : undefined;
            return (
              <MediaCard
                key={`${r.indexer}-${r.torrent_id}-${start + idx}`}
                cover={{ contentType, title: r.title }}
                coverShape={contentType === 'music' ? 'square' : 'poster'}
                title={r.title}
                source={indexerLabel(r.indexer)}
                meta={[
                  r.quality_label,
                  r.parsed_year != null ? String(r.parsed_year) : '',
                  r.parsed_audio_codec ?? '',
                  r.parsed_music_quality ?? '',
                  `Se: ${r.seeders} Le: ${r.leechers}`,
                  r.size,
                ].filter(Boolean)}
                showSeLe={true}
                overlay={overlay}
                primaryAction={
                  <button
                    type="button"
                    className="media-card-play-btn"
                    onClick={(e) => { e.stopPropagation(); onOpenAddModal(r); }}
                    aria-label={`Adicionar ${r.title} à fila`}
                  >
                    <IoAdd size={24} />
                  </button>
                }
                actions={
                  <div className="result-card-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="atum-btn"
                      onClick={() => onOpenFilesModal(r)}
                      aria-label="Ver lista de arquivos do torrent"
                    >
                      Ver arquivos
                    </button>
                    <button
                      type="button"
                      className="atum-btn atum-btn-primary"
                      onClick={() => onOpenAddModal(r)}
                      aria-label={`Adicionar ${r.title} à fila`}
                    >
                      Adicionar
                    </button>
                    {(contentType === 'movies' || contentType === 'tv') && (
                      <button
                        type="button"
                        className="atum-btn"
                        onClick={() =>
                          navigate('/detail', {
                            state: {
                              result: r,
                              searchParams: {
                                query,
                                limit: 1000,
                                sort_by: sortBy,
                                content_type: contentType,
                                music_category_only: false,
                              },
                              originalIndex,
                            },
                          })
                        }
                        aria-label={`Ver detalhes de ${r.title}`}
                      >
                        Detalhes
                      </button>
                    )}
                  </div>
                }
                onClick={() => onOpenFilesModal(r)}
                clickAriaLabel={`Ver lista de arquivos de ${r.title} (${indexerLabel(r.indexer)})`}
              />
            );
          })}
      </div>
      {filteredResultsLength > PAGE_SIZE && (
        <nav className="pagination" aria-label="Paginação dos resultados">
          <span className="pagination-info">
            Página {page} de {totalPages} ({filteredResultsLength} resultado(s))
          </span>
          <div className="pagination-buttons">
            <button type="button" disabled={page <= 1} onClick={() => setPage(1)} aria-label="Primeira página">«</button>
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Próxima</button>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage(totalPages)} aria-label="Última página">»</button>
          </div>
        </nav>
      )}
    </>
  );
}
