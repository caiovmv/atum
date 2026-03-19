import { IoDownload, IoClose } from 'react-icons/io5';

const SIZE_OPTIONS = [4, 8, 16, 32, 64, 128];

interface PlaylistDownloadPanelProps {
  open: boolean;
  onClose: () => void;
  selectedSize: number;
  setSelectedSize: (v: number) => void;
  playlistId: number;
}

export function PlaylistDownloadPanel({
  open,
  onClose,
  selectedSize,
  setSelectedSize,
  playlistId,
}: PlaylistDownloadPanelProps) {
  if (!open) return null;

  return (
    <div className="pd-download-panel">
      <span className="pd-download-label">Tamanho máximo:</span>
      <div className="pd-size-chips">
        {SIZE_OPTIONS.map((size) => (
          <button
            key={size}
            type="button"
            className={`pd-size-chip${selectedSize === size ? ' pd-size-chip--active' : ''}`}
            onClick={() => setSelectedSize(size)}
          >
            {size} GB
          </button>
        ))}
      </div>
      <a
        href={`/api/playlists/${playlistId}/download/zip?max_size_gb=${selectedSize}`}
        className="atum-btn atum-btn-primary"
        download
      >
        <IoDownload size={16} /> Baixar .zip ({selectedSize} GB máx)
      </a>
      <button type="button" className="pd-download-close" onClick={onClose}>
        <IoClose size={16} />
      </button>
    </div>
  );
}
