import type { ToastItem } from '../contexts/ToastContext';
import './ToastList.css';

interface ToastListProps {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}

export function ToastList({ toasts, onDismiss }: ToastListProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="atum-toast-list" role="region" aria-label="Notificações">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="atum-toast-item"
          role="alert"
          aria-live="polite"
        >
          <span className="atum-toast-message">{t.message}</span>
          <button
            type="button"
            className="atum-toast-dismiss"
            onClick={() => onDismiss(t.id)}
            aria-label="Fechar"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
