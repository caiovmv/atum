import { BottomSheet } from '../BottomSheet';

interface CoverRefreshBottomSheetProps {
  open: boolean;
  onClose: () => void;
  coverQuery: string;
  setCoverQuery: (v: string) => void;
  coverRefreshResult: { ok: boolean; message?: string } | null;
  coverRefreshing: boolean;
  onRefresh: () => void;
}

export function CoverRefreshBottomSheet({
  open,
  onClose,
  coverQuery,
  setCoverQuery,
  coverRefreshResult,
  coverRefreshing,
  onRefresh,
}: CoverRefreshBottomSheetProps) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Buscar Capa">
      <p className="atum-library-cover-hint">
        Busca nos serviços de enriquecimento (TMDB, iTunes). Altere o termo se a capa automática estiver errada.
      </p>
      <div className="atum-library-modal-form">
        <label>
          Termo de busca
          <input
            type="text"
            value={coverQuery}
            onChange={(e) => setCoverQuery(e.target.value)}
            placeholder="Nome do filme, série ou álbum"
          />
        </label>
      </div>
      {coverRefreshResult && (
        <p className={`atum-library-cover-result ${coverRefreshResult.ok ? 'atum-library-cover-result--ok' : 'atum-library-cover-result--error'}`}>
          {coverRefreshResult.message}
        </p>
      )}
      <div className="atum-library-modal-actions">
        <button type="button" className="atum-btn" onClick={onClose}>
          Fechar
        </button>
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          onClick={onRefresh}
          disabled={coverRefreshing}
        >
          {coverRefreshing ? 'Buscando…' : 'Buscar'}
        </button>
      </div>
    </BottomSheet>
  );
}
