import type { DownloadRow } from '../../hooks/useDownloads';
import { CoverImage } from '../CoverImage';
import { formatBytes, formatSpeed, formatEta, resolveContentType } from './downloadsUtils';

interface Props {
  rows: DownloadRow[];
  onStart: (id: number) => void;
  onStop: (id: number) => void;
  onRetry: (id: number) => void;
  onRemove: (id: number) => void;
}

export function DownloadsCards({ rows, onStart, onStop, onRetry, onRemove }: Props) {
  return (
    <div className="downloads-cards">
      {rows.map((row) => {
        const pct = Math.round((row.progress ?? 0) * 100);
        const speed = formatSpeed(row.download_speed_bps);
        const eta = formatEta(row.eta_seconds);

        return (
          <div key={row.id} className="download-card">
            <div className="download-card-cover">
              <CoverImage
                contentType={resolveContentType(row)}
                title={row.name ?? ''}
                size="thumb"
                downloadId={row.id}
              />
              {row.status === 'downloading' && (
                <div className="download-card-progress-overlay" aria-hidden>
                  <span style={{ color: '#fff', fontWeight: 700, fontSize: '0.9rem' }}>{pct}%</span>
                </div>
              )}
            </div>

            <div className="download-card-body">
              <div className="download-card-name" title={row.name}>{row.name ?? '—'}</div>

              <div className="download-card-meta">
                <span className={`status status-${row.status}`}>{row.status}</span>
                {speed && <span> · {speed}</span>}
                {eta && <span> · {eta}</span>}
                {row.total_bytes ? <span> · {formatBytes(row.total_bytes)}</span> : null}
              </div>

              {row.status === 'failed' && row.error_message && (
                <div className="download-card-error" role="alert">{row.error_message}</div>
              )}

              {row.status === 'downloading' && (
                <div className="progress-bar-wrap" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                  <div className="progress-bar" style={{ width: `${pct}%` }} />
                </div>
              )}

              <div className="download-card-actions">
                {(row.status === 'paused' || row.status === 'queued') && (
                  <button type="button" className="atum-btn atum-btn-small atum-btn-primary" onClick={() => onStart(row.id)}>Iniciar</button>
                )}
                {row.status === 'downloading' && (
                  <button type="button" className="atum-btn atum-btn-small" onClick={() => onStop(row.id)}>Pausar</button>
                )}
                {row.status === 'failed' && (
                  <button type="button" className="atum-btn atum-btn-small" onClick={() => onRetry(row.id)}>Tentar</button>
                )}
                <button type="button" className="atum-btn atum-btn-small atum-btn--danger" onClick={() => onRemove(row.id)}>Remover</button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
