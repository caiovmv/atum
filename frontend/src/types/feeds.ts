export interface Feed {
  id: number;
  url: string;
  title?: string;
  content_type: string;
  created_at?: string;
}

export interface PendingItem {
  id: number;
  feed_id: number;
  entry_id: string;
  title: string;
  link: string | null;
  quality_label: string;
  created_at?: string;
  content_type?: string;
}

export interface AIFeedSuggestion {
  url: string;
  title: string;
  reason: string;
  content_type: string;
}
