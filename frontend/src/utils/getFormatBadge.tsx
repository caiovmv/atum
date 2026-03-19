import { MdGraphicEq, MdTv } from 'react-icons/md';
import { FaMusic, FaFilm, FaMicrophoneAlt } from 'react-icons/fa';

const VIDEO_EXTS = /\.(mp4|mkv|avi|webm|mov|wmv|flv|m4v)$/i;
const SHOW_KEYWORDS = /\b(live|concert|show|festival|unplugged|tour|ao\s*vivo|mtv|acoustic|session)\b/i;

export interface FormatBadgeItem {
  content_type?: string;
  content_path?: string;
  name?: string;
  music_quality?: string;
  audio_codec?: string;
}

/**
 * Retorna ícone de badge para tipo de mídia (filme, série, FLAC, show, etc.).
 */
export function getFormatBadge(item: FormatBadgeItem): React.ReactNode {
  const ct = item.content_type;
  if (ct === 'movies') return <FaFilm size={12} />;
  if (ct === 'tv') return <MdTv size={13} />;

  const path = item.content_path || '';
  const name = item.name || '';
  if (VIDEO_EXTS.test(path) || SHOW_KEYWORDS.test(name))
    return <FaMicrophoneAlt size={12} />;

  const mq = (item.music_quality || '').toUpperCase();
  const ac = (item.audio_codec || '').toUpperCase();
  if (mq === 'FLAC' || ac === 'FLAC' || /\bflac\b/i.test(name) || /\blossless\b/i.test(name))
    return <MdGraphicEq size={13} />;

  return <FaMusic size={11} />;
}
