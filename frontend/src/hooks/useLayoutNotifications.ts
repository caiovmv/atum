import { useState, useCallback, useRef, useEffect } from 'react';
import {
  getUnreadCount,
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  clearNotifications,
  evictCache,
  type Notification,
} from '../api/notifications';

export function useLayoutNotifications(showToast: (msg: string, duration?: number) => void, notifOpen: boolean) {
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notifLoading, setNotifLoading] = useState(false);
  const [notifReconnecting, setNotifReconnecting] = useState(false);
  const notifSseRef = useRef<EventSource | null>(null);
  const showToastRef = useRef(showToast);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  showToastRef.current = showToast;

  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await getUnreadCount();
      setUnreadCount(count);
    } catch {
      if (import.meta.env.DEV) console.warn('[Layout] getUnreadCount failed');
    }
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    let disposed = false;
    let sseErrorCount = 0;
    let pollIntervalId: ReturnType<typeof setInterval> | null = null;
    const POLL_INTERVAL_MS = 15000;
    const SSE_ERROR_THRESHOLD = 2;

    const startPolling = () => {
      if (pollIntervalId) return;
      pollIntervalId = setInterval(() => {
        if (document.visibilityState === 'visible') fetchUnreadCount();
      }, POLL_INTERVAL_MS);
    };

    const stopPolling = () => {
      if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
      }
    };

    const open = () => {
      if (disposed || notifSseRef.current) return;
      const es = new EventSource('/api/notifications/events');
      es.onmessage = (event: MessageEvent) => {
        setNotifReconnecting(false);
        sseErrorCount = 0;
        stopPolling();
        evictCache('/api/notifications');
        try {
          const data = JSON.parse(event.data);
          if (typeof data.count === 'number') setUnreadCount(data.count);
        } catch {
          // ignore
        }
      };
      es.addEventListener('new_notification', ((event: MessageEvent) => {
        setNotifReconnecting(false);
        sseErrorCount = 0;
        stopPolling();
        evictCache('/api/notifications');
        try {
          const data = JSON.parse(event.data);
          if (typeof data.count === 'number') setUnreadCount(data.count);
          if (data.notification?.title) {
            showToastRef.current(data.notification.title, 6000);
          }
        } catch {
          // ignore
        }
      }) as EventListener);
      es.onerror = () => {
        setNotifReconnecting(true);
        es.close();
        notifSseRef.current = null;
        sseErrorCount += 1;
        if (sseErrorCount >= SSE_ERROR_THRESHOLD && document.visibilityState === 'visible') {
          startPolling();
          fetchUnreadCount();
          return;
        }
        if (!disposed) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      notifSseRef.current = es;
    };
    const close = () => {
      stopPolling();
      if (notifSseRef.current) {
        notifSseRef.current.close();
        notifSseRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (!notifOpen) return;
    const controller = new AbortController();
    setNotifLoading(true);
    getNotifications(30, { signal: controller.signal })
      .then(setNotifications)
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setNotifications([]);
      })
      .finally(() => setNotifLoading(false));
    return () => controller.abort();
  }, [notifOpen]);

  const markRead = useCallback(async (id: number) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      fetchUnreadCount();
    } catch {
      if (import.meta.env.DEV) console.warn('[Layout] markRead failed');
    }
  }, [fetchUnreadCount]);

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      if (import.meta.env.DEV) console.warn('[Layout] markAllRead failed');
    }
  }, []);

  const clearAll = useCallback(async () => {
    try {
      await clearNotifications();
      setNotifications([]);
      setUnreadCount(0);
    } catch {
      if (import.meta.env.DEV) console.warn('[Layout] clearAll failed');
    }
  }, []);

  return {
    unreadCount,
    notifications,
    notifLoading,
    notifReconnecting,
    markRead,
    markAllRead,
    clearAll,
  };
}
