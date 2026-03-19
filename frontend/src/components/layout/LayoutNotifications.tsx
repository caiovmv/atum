import { IoNotificationsOutline } from 'react-icons/io5';
import { BottomSheet } from '../BottomSheet';
import { SkeletonRow } from '../Skeleton';

interface LayoutNotificationsProps {
  open: boolean;
  onClose: () => void;
  onOpenChange: (open: boolean) => void;
  unreadCount: number;
  notifications: { id: number; title?: string; body?: string; read?: boolean; created_at?: string }[];
  loading: boolean;
  reconnecting: boolean;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onClearAll: () => void;
}

export function LayoutNotifications({
  open,
  onClose,
  onOpenChange,
  unreadCount,
  notifications,
  loading,
  reconnecting,
  onMarkRead,
  onMarkAllRead,
  onClearAll,
}: LayoutNotificationsProps) {
  return (
    <div className="atum-notifications-wrap">
      <button
        type="button"
        className="atum-notifications-btn"
        onClick={() => onOpenChange(!open)}
        aria-label={unreadCount > 0 ? `${unreadCount} não lidas` : 'Notificações'}
        aria-expanded={open}
      >
        <IoNotificationsOutline className="atum-notifications-icon" aria-hidden />
        {unreadCount > 0 && (
          <span className="atum-notifications-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>
      <BottomSheet open={open} onClose={onClose} title="Notificações">
        {reconnecting && <p className="atum-notifications-reconnecting" aria-live="polite">Reconectando…</p>}
        <div className="atum-notifications-actions atum-notifications-actions--spaced">
          {unreadCount > 0 && (
            <button type="button" className="atum-notifications-mark-all" onClick={onMarkAllRead}>
              Marcar todas como lidas
            </button>
          )}
          <button type="button" className="atum-notifications-clear" onClick={onClearAll}>
            Limpar
          </button>
        </div>
        <div className="atum-notifications-list">
          {loading ? (
            <div className="atum-notifications-skeleton" aria-busy="true">
              {Array.from({ length: 4 }, (_, i) => (
                <SkeletonRow key={i} />
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <p className="atum-notifications-empty">Nenhuma notificação.</p>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`atum-notification-item ${n.read ? 'read' : ''}`}
                role="button"
                tabIndex={0}
                aria-label={`${n.read ? '' : 'Marcar como lida: '}${n.title ?? ''}`}
                onClick={() => { if (!n.read) onMarkRead(n.id); }}
                onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && !n.read) onMarkRead(n.id); }}
              >
                <div className="atum-notification-title">{n.title ?? ''}</div>
                {n.body && <div className="atum-notification-body">{n.body}</div>}
                <div className="atum-notification-time">
                  {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                </div>
              </div>
            ))
          )}
        </div>
      </BottomSheet>
    </div>
  );
}
