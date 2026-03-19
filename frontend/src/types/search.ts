export interface SearchResult {
  title: string;
  quality_label: string;
  seeders: number;
  leechers: number;
  size: string;
  size_bytes: number;
  torrent_id: string;
  indexer: string;
  magnet: string | null;
  torrent_url?: string | null;
  parsed_year?: number | null;
  parsed_video_quality?: string | null;
  parsed_audio_codec?: string | null;
  parsed_music_quality?: string | null;
  parsed_cleaned_title?: string | null;
}

export interface FilterSuggestions {
  years: number[];
  genres: string[];
  qualities: string[];
}
