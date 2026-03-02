import { useState, useEffect } from 'react';
import './CoverImage.css';

type ContentType = 'music' | 'movies' | 'tv';

interface CoverImageProps {
  contentType: ContentType;
  title: string;
  size?: 'card' | 'thumb';
  alt?: string;
  /** Quando informado (ex.: lista de downloads), usa cache e preenche cache na primeira requisição */
  downloadId?: number;
}

export function CoverImage({ contentType, title, size = 'card', alt = '', downloadId }: CoverImageProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const apiSize = size === 'thumb' ? 'small' : 'large';

  useEffect(() => {
    if (!title.trim() && downloadId == null) return;
    let cancelled = false;
    const params = new URLSearchParams({ content_type: contentType, title: title.trim() || '', size: apiSize });
    if (downloadId != null) params.set('download_id', String(downloadId));
    fetch(`/api/cover?${params}`)
      .then((r) => (r.ok ? r.json() : { url: null }))
      .then((data) => {
        if (!cancelled && data?.url) setUrl(data.url);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => { cancelled = true; };
  }, [contentType, title, downloadId, apiSize]);

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
}
