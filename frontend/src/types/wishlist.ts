export interface WishlistTerm {
  id: number;
  term: string;
  created_at?: string;
}

export interface AISuggestion {
  term: string;
  reason: string;
  content_type: string;
}
