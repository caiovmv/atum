import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import { getPlaylists, getPlaylist, toggleFavorite as apiToggleFavorite } from '../api/playlists';

interface TrackKey {
  source: string;
  item_id: number;
  file_index: number;
}

function toKey(t: TrackKey): string {
  return `${t.source}:${t.item_id}:${t.file_index}`;
}

interface FavoritesContextType {
  isFavorited(source: string, itemId: number, fileIndex?: number): boolean;
  toggleFavorite(source: string, itemId: number, fileIndex?: number, fileName?: string): Promise<boolean>;
  favoritesSet: Set<string>;
}

const FavoritesCtx = createContext<FavoritesContextType | null>(null);

export function useFavorites(): FavoritesContextType {
  const ctx = useContext(FavoritesCtx);
  if (!ctx) throw new Error('useFavorites must be used within FavoritesProvider');
  return ctx;
}

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favSet, setFavSet] = useState<Set<string>>(new Set());

  const loadFavorites = useCallback(async () => {
    try {
      const playlists = await getPlaylists();
      const favPlaylist = playlists.find((p) => p.system_kind === 'favorites');
      if (!favPlaylist) return;

      const detail = await getPlaylist(String(favPlaylist.id));
      const tracks = detail.tracks || [];
      const set = new Set<string>();
      for (const t of tracks) {
        set.add(toKey({ source: t.source, item_id: t.item_id, file_index: t.file_index ?? 0 }));
      }
      setFavSet(set);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  const isFavorited = useCallback(
    (source: string, itemId: number, fileIndex = 0) => {
      return favSet.has(toKey({ source, item_id: itemId, file_index: fileIndex }));
    },
    [favSet],
  );

  const toggleFavorite = useCallback(
    async (source: string, itemId: number, fileIndex = 0, fileName?: string): Promise<boolean> => {
      try {
        const data = await apiToggleFavorite({ source, item_id: itemId, file_index: fileIndex, file_name: fileName });
        const key = toKey({ source, item_id: itemId, file_index: fileIndex });
        setFavSet(prev => {
          const next = new Set(prev);
          if (data.favorited) next.add(key);
          else next.delete(key);
          return next;
        });
        return data.favorited;
      } catch {
        return false;
      }
    },
    [],
  );

  const value = useMemo<FavoritesContextType>(
    () => ({ isFavorited, toggleFavorite, favoritesSet: favSet }),
    [isFavorited, toggleFavorite, favSet],
  );

  return (
    <FavoritesCtx.Provider value={value}>
      {children}
    </FavoritesCtx.Provider>
  );
}
