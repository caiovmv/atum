import { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { IoNotificationsOutline, IoHomeOutline, IoSearch, IoDownloadOutline, IoHeartOutline, IoReaderOutline, IoLibraryOutline, IoRadioOutline } from 'react-icons/io5';
import './Layout.css';

interface Notification {
  id: number;
  type: string;
  title: string;
  body?: string;
  payload?: Record<string, unknown>;
  read: boolean;
  created_at: string;
}

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notifLoading, setNotifLoading] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await fetch('/api/notifications/unread-count');
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.count ?? 0);
      }
    } catch {
      // ignore
    }
  }, []);

  const notifSseRef = useRef<EventSource | null>(null);
  const [notifReconnecting, setNotifReconnecting] = useState(false);
  useEffect(() => {
    fetchUnreadCount();
    const open = () => {
      if (notifSseRef.current) return;
      const es = new EventSource('/api/notifications/events');
      es.onmessage = (event) => {
        setNotifReconnecting(false);
        try {
          const data = JSON.parse(event.data);
          if (typeof data.count === 'number') setUnreadCount(data.count);
        } catch {
          // ignore
        }
      };
      es.onerror = () => {
        setNotifReconnecting(true);
        es.close();
      };
      notifSseRef.current = es;
    };
    const close = () => {
      if (notifSseRef.current) {
        notifSseRef.current.close();
        notifSseRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, []);

  useEffect(() => {
    if (!notifOpen) return;
    setNotifLoading(true);
    fetch('/api/notifications?limit=30')
      .then((r) => r.ok ? r.json() : [])
      .then((list) => setNotifications(Array.isArray(list) ? list : []))
      .catch(() => setNotifications([]))
      .finally(() => setNotifLoading(false));
  }, [notifOpen]);

  const markRead = async (id: number) => {
    try {
      await fetch(`/api/notifications/${id}/read`, { method: 'PATCH' });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      fetchUnreadCount();
    } catch {
      // ignore
    }
  };

  const markAllRead = async () => {
    try {
      await fetch('/api/notifications/mark-all-read', { method: 'POST' });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  const clearAll = async () => {
    try {
      await fetch('/api/notifications/clear', { method: 'POST' });
      setNotifications([]);
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  return (
    <div className="atum-layout">
      <button
        type="button"
        className="atum-menu-toggle"
        onClick={() => setMenuOpen((o) => !o)}
        aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
        aria-expanded={menuOpen}
      >
        <span className="atum-menu-toggle-bar" />
        <span className="atum-menu-toggle-bar" />
        <span className="atum-menu-toggle-bar" />
      </button>
      <div
        className="atum-sidebar-backdrop"
        aria-hidden
        data-open={menuOpen}
        onClick={() => setMenuOpen(false)}
      />
      <aside className="atum-sidebar" data-open={menuOpen}>
        <div className="atum-sidebar-brand">Atum</div>
        <nav className="atum-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoHomeOutline className="atum-nav-icon" aria-hidden />
            <span>Início</span>
          </NavLink>
          <NavLink to="/search" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoSearch className="atum-nav-icon" aria-hidden />
            <span>Busca</span>
          </NavLink>
          <NavLink to="/downloads" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoDownloadOutline className="atum-nav-icon" aria-hidden />
            <span>Downloads</span>
          </NavLink>
          <NavLink to="/wishlist" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoHeartOutline className="atum-nav-icon" aria-hidden />
            <span>Wishlist</span>
          </NavLink>
          <NavLink to="/feeds" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoReaderOutline className="atum-nav-icon" aria-hidden />
            <span>Feeds</span>
          </NavLink>
          <NavLink to="/library" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoLibraryOutline className="atum-nav-icon" aria-hidden />
            <span>Biblioteca</span>
          </NavLink>
          <NavLink to="/radio" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoRadioOutline className="atum-nav-icon" aria-hidden />
            <span>Rádio</span>
          </NavLink>
        </nav>
      </aside>
      <main className="atum-main">
        <div className="atum-main-header">
          <span />
          <div className="atum-notifications-wrap">
            <button
              type="button"
              className="atum-notifications-btn"
              onClick={() => setNotifOpen((o) => !o)}
              aria-label={unreadCount > 0 ? `${unreadCount} não lidas` : 'Notificações'}
              aria-expanded={notifOpen}
            >
              <IoNotificationsOutline className="atum-notifications-icon" aria-hidden />
              {unreadCount > 0 && (
                <span className="atum-notifications-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
              )}
            </button>
            {notifOpen && (
              <>
                <div
                  className="atum-notifications-backdrop"
                  aria-hidden
                  onClick={() => setNotifOpen(false)}
                />
                <div className="atum-notifications-panel" role="dialog" aria-label="Cronologia de notificações">
                  <div className="atum-notifications-panel-header">
                    <span>Notificações</span>
                    {notifReconnecting && <span className="atum-notifications-reconnecting" aria-live="polite">Reconectando…</span>}
                    <div className="atum-notifications-actions">
                      {unreadCount > 0 && (
                        <button type="button" className="atum-notifications-mark-all" onClick={markAllRead}>
                          Marcar todas como lidas
                        </button>
                      )}
                      <button type="button" className="atum-notifications-clear" onClick={clearAll}>
                        Limpar
                      </button>
                    </div>
                  </div>
                  <div className="atum-notifications-list">
                    {notifLoading ? (
                      <p className="atum-notifications-empty">Carregando…</p>
                    ) : notifications.length === 0 ? (
                      <p className="atum-notifications-empty">Nenhuma notificação.</p>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`atum-notification-item ${n.read ? 'read' : ''}`}
                          role="button"
                          tabIndex={0}
                          onClick={() => { if (!n.read) markRead(n.id); }}
                          onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && !n.read) markRead(n.id); }}
                        >
                          <div className="atum-notification-title">{n.title}</div>
                          {n.body && <div className="atum-notification-body">{n.body}</div>}
                          <div className="atum-notification-time">
                            {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
        <div className="atum-main-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
