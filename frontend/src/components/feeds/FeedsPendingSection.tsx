import { EmptyState } from '../EmptyState';
import { SkeletonRow } from '../Skeleton';
import type { PendingItem } from '../../types/feeds';

interface FeedsPendingSectionProps {
  pending: PendingItem[];
  pendingLoading: boolean;
  feedsReconnecting: boolean;
  selectedPending: Set<number>;
  organize: boolean;
  setOrganize: (v: boolean) => void;
  addToDownloadsRunning: boolean;
  onTogglePending: (id: number) => void;
  onSelectAll: () => void;
  onAddToDownloads: () => void;
}

export function FeedsPendingSection({
  pending,
  pendingLoading,
  feedsReconnecting,
  selectedPending,
  organize,
  setOrganize,
  addToDownloadsRunning,
  onTogglePending,
  onSelectAll,
  onAddToDownloads,
}: FeedsPendingSectionProps) {
  return (
    <section className="atum-feeds-pending-section" aria-labelledby="pending-heading">
      <h2 id="pending-heading" className="atum-feeds-section-title">Itens pendentes</h2>
      {feedsReconnecting && (
        <span className="atum-feeds-reconnecting" aria-live="polite">Reconectando…</span>
      )}
      {pendingLoading ? (
        <div className="atum-feeds-skeleton" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => <SkeletonRow key={i} />)}
        </div>
      ) : pending.length === 0 ? (
        <EmptyState
          title="Nenhum item pendente"
          description="Use &quot;Verificar feeds agora&quot; para buscar novidades."
        />
      ) : (
        <>
          <div className="atum-feeds-pending-controls">
            <label>
              <input
                type="checkbox"
                checked={selectedPending.size === pending.length && pending.length > 0}
                onChange={onSelectAll}
              />
              {' '}Selecionar todos
            </label>
            <label className="atum-feeds-pending-organize">
              <input
                type="checkbox"
                checked={organize}
                onChange={(e) => setOrganize(e.target.checked)}
              />
              {' '}Organizar em subpastas
            </label>
          </div>
          <ul className="atum-feeds-ul">
            {pending.map((p) => (
              <li key={p.id} className="atum-feeds-pending-item">
                <input
                  type="checkbox"
                  checked={selectedPending.has(p.id)}
                  onChange={() => onTogglePending(p.id)}
                  aria-label={`Selecionar ${p.title}`}
                />
                <div className="atum-feeds-pending-label">
                  <span>{p.title || '(sem título)'}</span>
                  <span className="atum-feeds-pending-quality"> [{p.quality_label || '?'}]</span>
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="atum-btn atum-btn-primary atum-feeds-pending-submit"
            onClick={onAddToDownloads}
            disabled={addToDownloadsRunning || selectedPending.size === 0}
          >
            {addToDownloadsRunning ? 'Enviando…' : 'Adicionar selecionados aos downloads'}
          </button>
        </>
      )}
    </section>
  );
}
