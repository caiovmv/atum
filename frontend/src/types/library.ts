/**
 * Tipos compartilhados para biblioteca e itens de mídia.
 */

export type ContentType = 'music' | 'movies' | 'tv' | 'concerts';

export interface LibraryItem {
  id: number;
  name?: string;
  content_type?: string;
  source?: 'download' | 'import';
  content_path?: string;
  artist?: string;
  album?: string;
  year?: number;
  genre?: string;
  tags?: string[];
  music_quality?: string;
  audio_codec?: string;
  video_quality_label?: string;
  cover_path_small?: string;
  cover_path_large?: string;
  status?: string;
  progress?: number;
}

export interface ActiveDownload {
  id: number;
  name?: string;
  content_type?: string;
  progress?: number;
  status?: string;
}

export interface Facets {
  artists: string[];
  albums: string[];
  genres: string[];
  tags: string[];
  moods: string[];
  sub_genres: string[];
  descriptors: string[];
}
