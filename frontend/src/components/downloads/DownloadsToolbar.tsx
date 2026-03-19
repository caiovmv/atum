interface StatusCounts {
  queued: number;
  downloading: number;
  paused: number;
  completed: number;
  failed: number;
}

interface Props {
  statusFilter: string;
  setStatusFilter: (f: string) => void;
  statusCounts: StatusCounts;
  onRefresh: () => void;
  loading: boolean;
  lastUpdatedStr: string;
  reconnecting: boolean;
}

const PILLS: { label: string; value: string; key: keyof StatusCounts }[] = [
  { label: 'Todos', value: '', key: 'queued' },
  { label: 'Baixando', value: 'downloading', key: 'downloading' },
  { label: 'Pausados', value: 'paused', key: 'paused' },
  { label: 'Concluídos', value: 'completed', key: 'completed' },
  { label: 'Falhos', value: 'failed', key: 'failed' },
  { label: 'Fila', value: 'queued', key: 'queued' },
];

const TOTAL_LABEL = 'Todos';

export function DownloadsToolbar({ statusFilter, setStatusFilter, statusCounts, onRefresh, loading, lastUpdatedStr, reconnecting }: Props) {
  const total = Object.values(statusCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="downloads-toolbar">
      <div className="downloads-pills" role="group" aria-label="Filtrar por status">
        {PILLS.map(({ label, value, key }) => {
          const count = label === TOTAL_LABEL ? total : statusCounts[key];
          const active = statusFilter === value;
          return (
            <button
              key={value || 'all'}
              type="button"
              className={`downloads-pill${active ? ' downloads-pill--active' : ''}`}
              aria-pressed={active}
              onClick={() => setStatusFilter(value)}
            >
              {label}
              {count > 0 && <span className="downloads-pill-count">{count}</span>}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        className="atum-btn atum-btn-small"
        onClick={onRefresh}
        disabled={loading}
        aria-label="Atualizar lista"
      >
        {loading ? '↻' : '↺'} Atualizar
      </button>

      {reconnecting && (
        <span style={{ color: 'var(--atum-warning)', fontSize: '0.85rem' }} aria-live="polite">
          Reconectando…
        </span>
      )}

      {lastUpdatedStr && !reconnecting && (
        <span className="downloads-last-updated" aria-live="polite">{lastUpdatedStr}</span>
      )}
    </div>
  );
}
