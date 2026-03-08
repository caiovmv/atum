import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

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
    fetch('/api/downloads')
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        if (!mountedRef.current) return;
        setDownloads(Array.isArray(list) ? list : []);
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let disposed = false;

    const open = () => {
      if (disposed || sseRef.current) return;
      const es = new EventSource('/api/downloads/events');
      es.onmessage = (event) => {
        setReconnecting(false);
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
