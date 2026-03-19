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

function Progress({ progress }: { progress?: number }) {
  const pct = Math.round((progress ?? 0) * 100);
  return (
    <>
      <span className="progress-text">{pct}%</span>
      <div className="progress-bar-wrap" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-bar" style={{ width: `${pct}%` }} />
      </div>
    </>
  );
}

export function DownloadsTable({ rows, onStart, onStop, onRetry, onRemove }: Props) {
  return (
    <div className="downloads-table-wrap">
      <table className="downloads-table">
        <thead>
          <tr>
            <th className="cover-th" aria-label="Capa" />
            <th>Nome</th>
            <th>Status</th>
            <th>Progresso</th>
            <th>Velocidade</th>
            <th>ETA</th>
            <th>Tamanho</th>
            <th>Seeds</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td className="cover-cell">
                <CoverImage
                  contentType={resolveContentType(row)}
                  title={row.name ?? ''}
                  size="thumb"
                  downloadId={row.id}
                />
              </td>
              <td className="name-cell" title={row.name}>{row.name ?? '—'}</td>
              <td>
                <span className={`status status-${row.status}`}>{row.status}</span>
                {row.status === 'failed' && row.error_message && (
                  <span className="download-error-hint" title={row.error_message}>⚠</span>
                )}
              </td>
              <td><Progress progress={row.progress} /></td>
              <td>{formatSpeed(row.download_speed_bps)}</td>
              <td>{formatEta(row.eta_seconds)}</td>
              <td>{formatBytes(row.total_bytes)}</td>
              <td>{row.num_seeds ?? '—'}</td>
              <td>
                {row.status === 'paused' || row.status === 'queued' ? (
                  <button type="button" className="atum-btn atum-btn-small atum-btn-primary" onClick={() => onStart(row.id)}>Iniciar</button>
                ) : row.status === 'downloading' ? (
                  <button type="button" className="atum-btn atum-btn-small" onClick={() => onStop(row.id)}>Pausar</button>
                ) : null}
                {row.status === 'failed' && (
                  <button type="button" className="atum-btn atum-btn-small" onClick={() => onRetry(row.id)}>Tentar</button>
                )}
                <button type="button" className="atum-btn atum-btn-small atum-btn--danger" onClick={() => onRemove(row.id)}>Remover</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
