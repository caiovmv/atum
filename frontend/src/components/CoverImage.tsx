import { useState, useEffect, memo } from 'react';
import { getCover } from '../api/cover';
import './CoverImage.css';

type ContentType = 'music' | 'movies' | 'tv' | 'concerts';

interface CoverImageProps {
  contentType: ContentType;
  title: string;
  size?: 'card' | 'thumb';
  alt?: string;
  downloadId?: number;
  importId?: number;
}

export const CoverImage = memo(function CoverImage({ contentType, title, size = 'card', alt = '', downloadId, importId }: CoverImageProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const apiSize = size === 'thumb' ? 'small' : 'large';

  useEffect(() => {
    if (!title.trim() && downloadId == null && importId == null) return;
    let cancelled = false;
    getCover({
      content_type: contentType,
      title: title.trim() || '',
      size: apiSize,
      ...(downloadId != null && { download_id: downloadId }),
      ...(importId != null && { import_id: importId }),
    })
      .then((data) => {
        if (!cancelled && data?.url) setUrl(data.url);
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('[CoverImage] fetch failed', err);
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => { cancelled = true; };
  }, [contentType, title, downloadId, importId, apiSize]);

  if (url) {
    return (
      <img
        src={url}
        alt={alt || title.slice(0, 50)}
        className={`cover-image cover-image--${size}`}
        loading="lazy"
        onError={() => setUrl(null)}
      />
    );
  }
  return (
    <div className={`cover-image cover-image--${size} cover-image--placeholder`} aria-hidden>
      {!loaded ? <span className="cover-image-dots">…</span> : null}
    </div>
  );
});
