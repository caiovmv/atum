import { useState, useEffect, useCallback, useRef, type DependencyList } from 'react';

export interface UseFetchResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook para data fetching com loading, error e refetch.
 * Usa AbortController para cancelar requests ao desmontar.
 * @param fetcher - Função que recebe AbortSignal e retorna Promise. Use useCallback se depender de props.
 * @param deps - Dependências que disparam refetch quando mudam (ex: [id])
 */
export function useFetch<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: DependencyList = []
): UseFetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refetch = useCallback(() => {
    setFetchKey((k) => k + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;

    setLoading(true);
    setError(null);

    fetcherRef.current(signal)
      .then((result) => {
        if (!signal.aborted) setData(result);
      })
      .catch((e) => {
        if (e instanceof DOMException && e.name === 'AbortError') return;
        if (!signal.aborted) {
          setError(e instanceof Error ? e.message : 'Erro desconhecido');
        }
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [fetchKey, ...deps]);

  return { data, loading, error, refetch };
}
