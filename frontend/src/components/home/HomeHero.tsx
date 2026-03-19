import { IoPlay } from 'react-icons/io5';
import { CoverImage } from '../CoverImage';
import type { LibraryItem } from '../../types/library';
import { toContentType } from '../../hooks/useHome';

interface HomeHeroProps {
  item: LibraryItem;
  isNowPlaying: boolean;
  onPlay: (item: LibraryItem) => void;
}

export function HomeHero({ item, isNowPlaying, onPlay }: HomeHeroProps) {
  return (
    <div
      className="home-hero"
      onClick={() => onPlay(item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onPlay(item);
      }}
      aria-label={`Reproduzir ${item.name}`}
    >
      <div className="home-hero-bg">
        <CoverImage
          contentType={toContentType(item.content_type)}
          title={item.name || ''}
          size="card"
          downloadId={item.source === 'import' ? undefined : item.id}
          importId={item.source === 'import' ? item.id : undefined}
        />
      </div>
      <div className="home-hero-content">
        <span className="home-hero-label">
          {isNowPlaying ? 'Tocando agora' : 'Destaque'}
        </span>
        <h2 className="home-hero-title">{item.name}</h2>
        {item.artist && <p className="home-hero-artist">{item.artist}</p>}
        <button
          type="button"
          className="home-hero-play"
          onClick={(e) => {
            e.stopPropagation();
            onPlay(item);
          }}
        >
          <IoPlay size={18} />
          <span>Reproduzir</span>
        </button>
      </div>
    </div>
  );
}
