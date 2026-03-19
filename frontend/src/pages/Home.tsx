import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import { IoPlay } from 'react-icons/io5';
import { CoverImage } from '../components/CoverImage';
import { EmptyState } from '../components/EmptyState';
import { ContentRail } from '../components/ContentRail';
import { SkeletonHero, SkeletonRail } from '../components/Skeleton';
import { HomeHero } from '../components/home/HomeHero';
import { HomeActiveDownloads } from '../components/home/HomeActiveDownloads';
import { useHome, toContentType } from '../hooks/useHome';
import { getFormatBadge } from '../utils/getFormatBadge';
import type { LibraryItem } from '../types/library';
import './Home.css';

export function Home() {
  const home = useHome();

  const renderRailCard = useCallback(
    (item: LibraryItem) => (
      <button
        type="button"
        className="content-rail-card"
        onClick={() => home.playUrl(item)}
        aria-label={`Reproduzir ${item.name || 'item'}`}
      >
        <div className="content-rail-card-cover">
          <CoverImage
            contentType={toContentType(item.content_type)}
            title={item.name || ''}
            size="card"
            downloadId={item.source === 'import' ? undefined : item.id}
            importId={item.source === 'import' ? item.id : undefined}
          />
          <span className="content-rail-card-badge" aria-hidden>
            {getFormatBadge(item)}
          </span>
          <span className="content-rail-card-play" aria-hidden>
            <IoPlay size={24} />
          </span>
        </div>
        <span className="content-rail-card-title">{item.name || '—'}</span>
        {item.artist && <span className="content-rail-card-sub">{item.artist}</span>}
      </button>
    ),
    [home.playUrl]
  );

  return (
    <div className="atum-page home-page">
      <h1 className="home-greeting">{home.greeting}</h1>

      {home.heroItem && (
        <HomeHero
          item={home.heroItem}
          isNowPlaying={!!home.nowPlayingTrack && home.heroItem.id === home.nowPlayingTrack.id}
          onPlay={home.playUrl}
        />
      )}

      <HomeActiveDownloads downloads={home.activeDownloads} />

      {home.error && (
        <div className="home-error" role="alert">
          <p>{home.error}</p>
          <button type="button" className="home-retry-btn" onClick={home.refetch}>
            Tentar novamente
          </button>
        </div>
      )}

      {home.loading && home.allItems.length === 0 && !home.error && (
        <>
          <SkeletonHero />
          <SkeletonRail />
          <SkeletonRail />
        </>
      )}

      <ContentRail
        title="Recentes"
        items={home.recentItems}
        linkTo="/library"
        renderItem={renderRailCard}
        getKey={(item) => `${item.source ?? 'download'}-${item.id}`}
      />
      <ContentRail
        title="Música"
        items={home.musicItems.slice(0, 20)}
        linkTo="/library?type=music"
        renderItem={renderRailCard}
        getKey={(item) => `${item.source ?? 'download'}-${item.id}`}
      />
      <ContentRail
        title="Filmes & Séries"
        items={home.videoItems.slice(0, 20)}
        linkTo="/library?type=video"
        renderItem={renderRailCard}
        getKey={(item) => `${item.source ?? 'download'}-${item.id}`}
      />

      {!home.loading && home.allItems.length === 0 && (
        <EmptyState
          title="Sua biblioteca está vazia"
          description="Comece buscando algo para baixar ou importe suas pastas de mídia."
          action={
            <div className="home-empty-actions">
              <Link to="/search" className="home-empty-btn home-empty-btn--primary">
                Buscar
              </Link>
              <Link to="/library" className="home-empty-btn">
                Biblioteca
              </Link>
            </div>
          }
        />
      )}
    </div>
  );
}
