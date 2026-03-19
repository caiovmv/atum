import { BottomSheet } from '../BottomSheet';

interface Props {
  open: boolean;
  downloadId: number | null;
  onConfirm: (id: number) => void;
  onCancel: () => void;
}

export function DownloadsRemoveModal({ open, downloadId, onConfirm, onCancel }: Props) {
  return (
    <BottomSheet open={open} onClose={onCancel} title="Remover download" showCloseButton>
      <p style={{ color: 'var(--atum-text-muted)', marginBottom: '1.25rem' }}>
        Tem certeza que deseja remover este download da fila?
      </p>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          type="button"
          className="atum-btn atum-btn--danger"
          onClick={() => downloadId != null && onConfirm(downloadId)}
        >
          Remover
        </button>
        <button type="button" className="atum-btn" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </BottomSheet>
  );
}
