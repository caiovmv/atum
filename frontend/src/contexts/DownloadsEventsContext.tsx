import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

/** Formato de item de download vindo da API (lista). */
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
  const errorCountRef = useRef(0);

  const refetch = useCallback(() => {
    fetch('/api/downloads')
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        setDownloads(Array.isArray(list) ? list : []);
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, []);

  const open = useCallback(() => {
    if (sseRef.current) return;
    const es = new EventSource('/api/downloads/events');
    es.onmessage = (event) => {
      errorCountRef.current = 0;
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
      errorCountRef.current += 1;
      setReconnecting(true);
      es.close();
    };
    sseRef.current = es;
  }, []);

  const close = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, []);

  useEffect(() => {
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
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, [open, close, refetch]);

  return (
    <DownloadsEventsContext.Provider value={{ downloads, lastUpdated, refetch, reconnecting }}>
      {children}
    </DownloadsEventsContext.Provider>
  );
}

export function useDownloadsEvents(): DownloadsEventsState {
  return useContext(DownloadsEventsContext);
}
