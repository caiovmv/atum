import { type ReactNode, memo } from 'react';
import { CoverImage } from './CoverImage';
import './MediaCard.css';

type ContentType = 'music' | 'movies' | 'tv';

export interface MediaCardCoverProps {
  contentType?: ContentType;
  title?: string;
  downloadId?: number;
  importId?: number;
  src?: string;
  alt?: string;
}

export interface MediaCardOverlay {
  type: 'progress' | 'status';
  label: string;
  percent?: number;
}

export type MediaCardCoverShape = 'poster' | 'square';

export interface MediaCardProps {
  cover: MediaCardCoverProps;
  title: string;
  source?: string;
  meta: string[];
  showSeLe?: boolean;
  overlay?: MediaCardOverlay;
  /** Ações exibidas abaixo do título (botões, links). */
  actions: ReactNode;
  /** Ação principal exibida sobre a capa no hover (ex.: play, adicionar). */
  primaryAction?: ReactNode;
  /** Proporção da capa: poster 2/3 (filmes/séries), square 1/1 (música). */
  coverShape?: MediaCardCoverShape;
  onClick?: () => void;
  /** Quando onClick está definido, usa este label no botão (acessibilidade). */
  clickAriaLabel?: string;
}

export const MediaCard = memo(function MediaCard({
  cover,
  title,
  source,
  meta,
  showSeLe = true,
  overlay,
  actions,
  primaryAction,
  coverShape = 'poster',
  onClick,
  clickAriaLabel,
}: MediaCardProps) {
  const coverContent = cover.src ? (
    <img
      src={cover.src}
      alt={cover.alt ?? title.slice(0, 50)}
      className="media-card-cover-img"
      loading="lazy"
    />
  ) : (
    <CoverImage
      contentType={(cover.contentType ?? 'music') as ContentType}
      title={cover.title ?? title}
      size="card"
      downloadId={cover.downloadId}
      importId={cover.importId}
      alt={cover.alt ?? title}
    />
  );

  const coverArea = (
    <div className={`media-card-cover-wrap media-card-cover-wrap--${coverShape}`}>
      {coverContent}
      {overlay && (
        <div className="media-card-overlay" aria-hidden>
          <span className="media-card-overlay-label">{overlay.label}</span>
          {overlay.percent != null && (
            <span className="media-card-overlay-percent">{overlay.percent}%</span>
          )}
        </div>
      )}
      {primaryAction != null && (
        <div className="media-card-cover-hover-action" aria-hidden>
          {primaryAction}
        </div>
      )}
    </div>
  );

  const clickable = typeof onClick === 'function';

  return (
    <article className="media-card">
      {clickable ? (
        <button
          type="button"
          className="media-card-clickable"
          onClick={onClick}
          aria-label={clickAriaLabel ?? (source ? `Ver detalhes de ${title} (${source})` : `Ver detalhes de ${title}`)}
        >
          {coverArea}
          {source && <span className="media-card-source">{source}</span>}
          <div className="media-card-title">{title}</div>
        </button>
      ) : (
        <>
          {coverArea}
          {source && <span className="media-card-source">{source}</span>}
          <div className="media-card-title">{title}</div>
        </>
      )}
      <div className="media-card-meta">
        {meta.filter(Boolean).map((tag, i) => (
          <span key={i}>{tag}</span>
        ))}
        {showSeLe === false && meta.length === 0 && null}
      </div>
      <div className="media-card-actions">{actions}</div>
    </article>
  );
});
