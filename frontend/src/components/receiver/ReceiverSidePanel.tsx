import type React from 'react';
import { ReceiverSidePanelContent } from './ReceiverSidePanelContent';
import type { LibraryFile } from '../../api/library';

interface RadioQueueItem {
  id: number;
  source?: string;
  file_index?: number;
  file_name?: string;
  item_name?: string;
  artist?: string;
  name?: string;
  content_type?: string;
}

interface ReceiverSidePanelProps {
  item: { id: number; name?: string; content_type?: string; source?: string };
  files: LibraryFile[];
  isImport: boolean;
  isRadio: boolean;
  radioQueue: RadioQueueItem[] | null;
  activeRadioQueueIndex: number;
  safeFileIndex: number;
  currentFile: LibraryFile | { name: string; size: number; index: number };
  qualityMeta: { codec?: string; bitrate?: string | number } | null;
  trackFavorited: boolean;
  onToggleFav: () => void;
  rpPlaylistOpen: boolean;
  setRpPlaylistOpen: React.Dispatch<React.SetStateAction<boolean>>;
  rpPlaylists: { id: number; name: string }[];
  rpPlaylistRef: React.RefObject<HTMLDivElement | null>;
  onAddToPlaylist: (playlistId: number) => void;
  savingQueue: boolean;
  onSaveQueueAsPlaylist: () => void;
  goToQueueTrack: (index: number) => void;
  goToFileTrack: (index: number) => void;
  aiInsight: string | null;
  aiLoading: boolean;
  onFetchAiInsight: () => void;
  sideOpen: boolean;
  sheetRef: React.RefObject<HTMLElement | null>;
  onSheetTouchStart: (e: React.TouchEvent) => void;
  onSheetTouchMove: (e: React.TouchEvent) => void;
  onSheetTouchEnd: () => void;
}

export function ReceiverSidePanel(props: ReceiverSidePanelProps) {
  const { sideOpen, sheetRef, onSheetTouchStart, onSheetTouchMove, onSheetTouchEnd } = props;

  return (
    <aside
      ref={sheetRef}
      className={`receiver-side-panel${sideOpen ? '' : ' receiver-side-panel--collapsed'}`}
      onTouchStart={onSheetTouchStart}
      onTouchMove={onSheetTouchMove}
      onTouchEnd={onSheetTouchEnd}
      onTouchCancel={onSheetTouchEnd}
    >
      <div className="receiver-side-frame">
        <div className="receiver-side-glass">
          <ReceiverSidePanelContent {...props} />
        </div>
      </div>
    </aside>
  );
}
