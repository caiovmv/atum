import { useState } from 'react';

interface PlaylistCoverProps {
  playlistId: number;
  fallbackIcon: React.ReactNode;
  className?: string;
}

export function PlaylistCover({ playlistId, fallbackIcon, className }: PlaylistCoverProps) {
  const [useFallback, setUseFallback] = useState(false);
  if (useFallback) {
    return <div className="pd-header-icon">{fallbackIcon}</div>;
  }
  return (
    <img
      src={`/api/playlists/${playlistId}/cover`}
      alt=""
      className={className}
      onError={() => setUseFallback(true)}
    />
  );
}
