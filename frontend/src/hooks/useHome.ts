import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNowPlaying } from '../contexts/NowPlayingContext';
import { useFetch } from './useFetch';
import { getLibrary } from '../api/library';
import { getDownloads } from '../api/downloads';
import type { LibraryItem, ActiveDownload, ContentType } from '../types/library';

export function normalizeProgress(p: number | undefined | null): number {
  if (p == null) return 0;
  return Math.min(100, p <= 1 ? p * 100 : p);
}

export function getGreeting(): string {
  const h = new Date().getHours();
  if (h >= 5 && h < 12) return 'Bom dia';
  if (h >= 12 && h < 18) return 'Boa tarde';
  return 'Boa noite';
}

export function toContentType(ct: string | undefined): ContentType {
  if (ct === 'movies' || ct === 'tv' || ct === 'concerts') return ct;
  return 'music';
}

export function useHome() {
  const navigate = useNavigate();
  const { track: nowPlayingTrack } = useNowPlaying();

  const { data, loading, error, refetch } = useFetch(
    (signal) =>
      Promise.all([
        getLibrary({}, { staleMs: 30_000, signal }).catch(() => {
          throw new Error('Erro ao carregar biblioteca');
        }),
        getDownloads('downloading', { signal }).catch(() => []),
      ]).then(([lib, dls]) => ({
        allItems: lib.filter((x) => x.content_path),
        activeDownloads: dls.filter((d) => d.status === 'downloading'),
      })),
    []
  );

  const allItems = data?.allItems ?? [];
  const activeDownloads = (data?.activeDownloads ?? []) as ActiveDownload[];

  const playUrl = useCallback(
    (item: LibraryItem) => {
      if (!item.content_path) return;
      const q = item.source === 'import' ? '?source=import' : '';
      const playBase =
        item.content_type === 'movies' || item.content_type === 'tv' ? '/play' : '/play-receiver';
      navigate(`${playBase}/${item.id}${q}`);
    },
    [navigate]
  );

  const musicItems = allItems.filter(
    (i) =>
      i.content_type === 'music' ||
      !i.content_type ||
      (i.content_type !== 'movies' && i.content_type !== 'tv')
  );
  const videoItems = allItems.filter(
    (i) => i.content_type === 'movies' || i.content_type === 'tv'
  );
  const recentItems = allItems.slice(0, 20);

  const heroItem = nowPlayingTrack
    ? allItems.find((i) => i.id === nowPlayingTrack.id) ?? allItems[0]
    : allItems[0];

  return {
    greeting: getGreeting(),
    allItems,
    activeDownloads,
    musicItems,
    videoItems,
    recentItems,
    heroItem,
    nowPlayingTrack,
    loading,
    error,
    refetch,
    playUrl,
  };
}
