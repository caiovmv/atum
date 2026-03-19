import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { getDownloads } from '../api/downloads';

export interface DownloadItem {
  id: number;
  status?: string;
  name?: string;
  magnet?: string;
  progress?: number;
  num_seeds?: number;
  num_peers?: number;
  num_leechers?: number | null;
  [key: string]: unknown;
}

interface DownloadsEventsState {
  downloads: DownloadItem[];
  lastUpdated: Date | null;
  refetch: () => void;
  reconnecting: boolean;
}

const defaultState: DownloadsEventsState = {
  downloads: [],
  lastUpdated: null,
  refetch: () => {},
  reconnecting: false,
};

const DownloadsEventsContext = createContext<DownloadsEventsState>(defaultState);

export function DownloadsEventsProvider({ children }: { children: React.ReactNode }) {
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const sseRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const refetch = useCallback(() => {
    getDownloads()
      .then((list) => {
        if (!mountedRef.current) return;
        setDownloads(list);
        setLastUpdated(new Date());
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('[DownloadsEvents] initial fetch failed', err);
      });
  }, []);

  useEffect(() => {
    let disposed = false;
    let sseErrorCount = 0;
    let pollIntervalId: ReturnType<typeof setInterval> | null = null;
    const POLL_INTERVAL_MS = 15000;
    const SSE_ERROR_THRESHOLD = 2;

    const startPolling = () => {
      if (pollIntervalId) return;
      pollIntervalId = setInterval(() => {
        if (document.visibilityState === 'visible') refetch();
      }, POLL_INTERVAL_MS);
    };

    const stopPolling = () => {
      if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
      }
    };

    const open = () => {
      if (disposed || sseRef.current) return;
      const es = new EventSource('/api/downloads/events');
      es.onmessage = (event: MessageEvent) => {
        setReconnecting(false);
        sseErrorCount = 0;
        stopPolling();
        try {
          const data = JSON.parse(event.data);
          setDownloads(Array.isArray(data) ? data : []);
          setLastUpdated(new Date());
        } catch {
          // ignore
        }
      };
      es.onerror = () => {
        setReconnecting(true);
        es.close();
        sseRef.current = null;
        sseErrorCount += 1;
        if (sseErrorCount >= SSE_ERROR_THRESHOLD && document.visibilityState === 'visible') {
          startPolling();
          refetch();
          return;
        }
        if (!disposed) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      sseRef.current = es;
    };

    const close = () => {
      stopPolling();
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
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

    if (document.visibilityState === 'visible') {
      open();
      refetch();
    }
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, [refetch]);

  return (
    <DownloadsEventsContext.Provider value={{ downloads, lastUpdated, refetch, reconnecting }}>
      {children}
    </DownloadsEventsContext.Provider>
  );
}

export function useDownloadsEvents(): DownloadsEventsState {
  return useContext(DownloadsEventsContext);
}
