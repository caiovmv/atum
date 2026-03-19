import { Link } from 'react-router-dom';
import { useDownloads } from '../hooks/useDownloads';
import { EmptyState } from '../components/EmptyState';
import { SkeletonRow } from '../components/Skeleton';
import { DownloadsRemoveModal } from '../components/downloads/DownloadsRemoveModal';
import { DownloadsToolbar } from '../components/downloads/DownloadsToolbar';
import { DownloadsTable } from '../components/downloads/DownloadsTable';
import { DownloadsCards } from '../components/downloads/DownloadsCards';
import './Downloads.css';

export function Downloads() {
  const {
    rows,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    statusCounts,
    lastUpdated,
    reconnecting,
    removeModalId,
    setRemoveModalId,
    fetchDownloads,
    contextRefetch,
    handleStart,
    handleStop,
    handleRemove,
    handleRetry,
  } = useDownloads();

  const lastUpdatedStr = lastUpdated ? `Atualizado há ${Math.round((Date.now() - lastUpdated.getTime()) / 1000)} s` : '';

  return (
    <div className="atum-page downloads-page">
      <h1 className="atum-page-title">Downloads</h1>

      <DownloadsRemoveModal
        open={removeModalId != null}
        downloadId={removeModalId}
        onConfirm={handleRemove}
        onCancel={() => setRemoveModalId(null)}
      />

      <DownloadsToolbar
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        statusCounts={statusCounts}
        onRefresh={() => fetchDownloads()}
        loading={loading}
        lastUpdatedStr={lastUpdatedStr}
        reconnecting={reconnecting}
      />

      {error && (
        <div className="downloads-error" role="alert">
          <p>{error}</p>
          <button type="button" className="atum-btn atum-btn-primary downloads-retry-btn" onClick={() => contextRefetch()}>
            Tentar novamente
          </button>
        </div>
      )}

      {loading && rows.length === 0 ? (
        <div aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => <SkeletonRow key={i} />)}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nenhum download na fila"
          description="Busque torrents e adicione à fila para começar."
          action={<Link to="/search">Ir à busca</Link>}
        />
      ) : (
        <>
          <DownloadsTable
            rows={rows}
            onStart={handleStart}
            onStop={handleStop}
            onRetry={handleRetry}
            onRemove={setRemoveModalId}
          />
          <DownloadsCards
            rows={rows}
            onStart={handleStart}
            onStop={handleStop}
            onRetry={handleRetry}
            onRemove={setRemoveModalId}
          />
        </>
      )}
    </div>
  );
}
