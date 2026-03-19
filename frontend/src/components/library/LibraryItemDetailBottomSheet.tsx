import { useEffect, useRef, useState } from 'react';
import { IoDownloadOutline } from 'react-icons/io5';
import { BottomSheet } from '../BottomSheet';
import { CoverImage } from '../CoverImage';
import { Skeleton } from '../Skeleton';
import { getLibraryItemDetail, uploadImportedCover } from '../../api/library';
import { useToast } from '../../contexts/ToastContext';
import { useOfflineSave } from '../../hooks/useOfflineSave';
import { hasFileSystemAccessSupport } from '../../utils/fileSystemAccess';
import type { LibraryItem, ContentType } from '../../types/library';
import type { LibraryItemDetailFull } from '../../api/library';

function toContentType(ct: string | undefined): ContentType {
  return ct === 'movies' || ct === 'tv' ? ct : 'music';
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function coverSourceLabel(src: string | undefined): string {
  const map: Record<string, string> = {
    folder: 'Pasta (folder.jpg, cover.jpg)',
    embedded: 'Arquivo de áudio',
    tmdb: 'TMDB',
    itunes: 'iTunes',
    imdb: 'IMDB',
    llm: 'LLM',
    user: 'Upload manual',
  };
  return (src && map[src]) || src || '—';
}

interface LibraryItemDetailBottomSheetProps {
  open: boolean;
  onClose: () => void;
  item: LibraryItem | null;
  onEdit: (item: LibraryItem) => void;
  onCoverUpdate?: (importId: number) => void;
}

export function LibraryItemDetailBottomSheet({
  open,
  onClose,
  item,
  onEdit,
  onCoverUpdate,
}: LibraryItemDetailBottomSheetProps) {
  const [detail, setDetail] = useState<LibraryItemDetailFull | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [coverUploading, setCoverUploading] = useState(false);
  const [coverUploadError, setCoverUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();
  const { save, saving, progress } = useOfflineSave({
    itemId: item?.id ?? 0,
    isImport: item?.source === 'import',
    onSuccess: (saved) => showToast(`${saved} arquivo(s) salvo(s) na pasta escolhida.`, 4000),
    onError: (msg) => showToast(msg, 5000),
  });

  useEffect(() => {
    if (!open || !item || item.source !== 'import') {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    const ctrl = new AbortController();
    getLibraryItemDetail(item.id, { signal: ctrl.signal })
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
    return () => ctrl.abort();
  }, [open, item?.id, item?.source]);

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !item || item.source !== 'import') return;
    setCoverUploadError(null);
    setCoverUploading(true);
    try {
      await uploadImportedCover(item.id, file);
      setDetail((d) => (d ? { ...d, cover_source: 'user' } : null));
      onCoverUpdate?.(item.id);
    } catch (err) {
      setCoverUploadError(err instanceof Error ? err.message : 'Erro ao enviar.');
    } finally {
      setCoverUploading(false);
      e.target.value = '';
    }
  };

  if (!item) return null;

  const ct = toContentType(item.content_type);
  const rawCt = (item.content_type || 'music').toLowerCase();
  const ctLabel = rawCt === 'movies' ? 'Filme' : rawCt === 'tv' ? 'Série' : rawCt === 'concerts' ? 'Concerto' : 'Música';

  const files = detail?.files?.files ?? [];
  const folderStats = detail?.folder_stats;
  const metadata = detail?.metadata_json as Record<string, unknown> | undefined;
  const format = metadata?.format as Record<string, unknown> | undefined;
  const streams = (metadata?.streams as unknown[]) ?? [];
  const duration = metadata?.duration_seconds ?? format?.duration;
  const codecVal = metadata?.codec ?? (streams[0] as Record<string, unknown>)?.codec_name;
  const codec = codecVal != null ? String(codecVal) : undefined;

  return (
    <BottomSheet open={open} onClose={onClose} title="Detalhes" showCloseButton>
      <div className="atum-library-detail">
        <div className="atum-library-detail-cover">
          <CoverImage
            contentType={ct}
            title={item.name || ''}
            downloadId={item.source === 'import' ? undefined : item.id}
            importId={item.source === 'import' ? item.id : undefined}
            size="card"
          />
          {item.source === 'import' && (
            <div className="atum-library-detail-cover-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="atum-library-cover-upload-input"
                onChange={handleCoverUpload}
                aria-label="Upload de capa"
              />
              <button
                type="button"
                className="atum-btn atum-btn-ghost atum-library-cover-upload-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={coverUploading}
              >
                {coverUploading ? 'Enviando…' : 'Upload capa'}
              </button>
              {coverUploadError && (
                <p className="atum-library-cover-upload-error" role="alert">
                  {coverUploadError}
                </p>
              )}
            </div>
          )}
        </div>
        <div className="atum-library-detail-meta">
          <h3 className="atum-library-detail-title">{item.name || '—'}</h3>
          <dl className="atum-library-detail-list">
            <dt>Tipo</dt>
            <dd>{ctLabel}</dd>
            {item.artist && (
              <>
                <dt>Artista</dt>
                <dd>{item.artist}</dd>
              </>
            )}
            {item.album && (
              <>
                <dt>Álbum</dt>
                <dd>{item.album}</dd>
              </>
            )}
            {item.year && (
              <>
                <dt>Ano</dt>
                <dd>{item.year}</dd>
              </>
            )}
            {item.genre && (
              <>
                <dt>Gênero</dt>
                <dd>{item.genre}</dd>
              </>
            )}
            {(item.tags || []).length > 0 && (
              <>
                <dt>Tags</dt>
                <dd>{(item.tags || []).join(', ')}</dd>
              </>
            )}
            {item.source === 'import' && (
              <>
                <dt>Fonte da capa</dt>
                <dd>{detailLoading ? <Skeleton width="8rem" height="1em" /> : coverSourceLabel(detail?.cover_source)}</dd>
              </>
            )}
          </dl>

          {item.source === 'import' && (
            <>
              {folderStats && (
                <section className="atum-library-detail-section">
                  <h4 className="atum-library-detail-section-title">Pasta</h4>
                  <dl className="atum-library-detail-list">
                    <dt>Caminho</dt>
                    <dd className="atum-library-detail-path">{folderStats.path}</dd>
                    <dt>Pasta pai</dt>
                    <dd className="atum-library-detail-path">{folderStats.parent}</dd>
                  </dl>
                </section>
              )}

              {files.length > 0 && (
                <section className="atum-library-detail-section">
                  <h4 className="atum-library-detail-section-title">Arquivos ({files.length})</h4>
                  <ul className="atum-library-detail-files">
                    {files.map((f: { index?: number; name?: string; size?: number }) => (
                      <li key={f.index ?? f.name}>
                        {f.name} — {formatBytes(f.size ?? 0)}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {(metadata?.duration_seconds ?? format ?? codec) && (
                <section className="atum-library-detail-section">
                  <h4 className="atum-library-detail-section-title">Formato (FFprobe)</h4>
                  <dl className="atum-library-detail-list">
                    {format?.format_name != null && (
                      <>
                        <dt>Formato</dt>
                        <dd>{String(format.format_name)}</dd>
                      </>
                    )}
                    {duration != null && (
                      <>
                        <dt>Duração</dt>
                        <dd>{Number(duration).toFixed(1)} s</dd>
                      </>
                    )}
                    {format?.bit_rate != null && (
                      <>
                        <dt>Bitrate</dt>
                        <dd>{Math.round(Number(format.bit_rate) / 1000)} kbps</dd>
                      </>
                    )}
                    {codec != null && codec !== '' && (
                      <>
                        <dt>Codec</dt>
                        <dd>{String(codec)}</dd>
                      </>
                    )}
                  </dl>
                  {streams.length > 0 && (
                    <>
                      <h5 className="atum-library-detail-streams-title">Streams</h5>
                      {streams.slice(0, 3).map((s, i) => {
                        const stream = s as Record<string, unknown>;
                        return (
                          <div key={i} className="atum-library-detail-stream">
                            {String(stream.codec_type ?? '')}: {String(stream.codec_name ?? '')}
                            {stream.sample_rate != null && ` @ ${stream.sample_rate} Hz`}
                            {stream.width != null && stream.height != null && ` ${stream.width}x${stream.height}`}
                          </div>
                        );
                      })}
                    </>
                  )}
                </section>
              )}
            </>
          )}

          {hasFileSystemAccessSupport() && (
            <button
              type="button"
              className="atum-btn atum-btn-ghost"
              onClick={() => save()}
              disabled={saving}
              aria-label="Salvar para offline"
            >
              <IoDownloadOutline size={18} aria-hidden />
              {saving && progress
                ? `Salvando ${progress.current}/${progress.total}…`
                : 'Salvar para offline'}
            </button>
          )}

          {item.source === 'import' && (
            <button
              type="button"
              className="atum-btn atum-btn-primary"
              onClick={() => onEdit(item)}
            >
              Editar metadados
            </button>
          )}
        </div>
      </div>
    </BottomSheet>
  );
}
