import { apiGet, apiJson, evictCache } from './client';

export interface ContextField {
  name: string;
  type: string;
  label: string;
  placeholder?: string;
  required?: boolean;
}

export interface PromptItem {
  id: string;
  label: string;
  description: string;
  system: string;
  temperature: number;
  default_temperature: number;
  context_schema?: ContextField[];
  expected_json_schema?: string | null;
  response_type?: 'text' | 'json';
}

export async function getAIPrompts(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<PromptItem[]> {
  const data = await apiGet<PromptItem[]>('/api/ai/prompts', { staleMs: 30_000, ...options });
  return Array.isArray(data) ? data : [];
}

export async function updateAIPrompt(
  id: string,
  body: { system?: string; temperature?: number }
): Promise<void> {
  await apiJson<unknown>(`/api/ai/prompts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  evictCache('/api/ai/prompts');
}

export async function getAIRecommendations(
  target: 'feeds' | 'wishlist',
  limit = 5
): Promise<{ feed_suggestions?: Array<{ url: string; title: string; reason: string; content_type: string }>; wishlist_suggestions?: Array<{ term: string; reason: string; content_type: string }> }> {
  return apiJson('/api/ai/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target, limit }),
  });
}

export async function dryRunAIPrompt(
  id: string,
  body: { user_input?: string; context?: Record<string, string | number> }
): Promise<{ messages: Array<{ role: string; content: string }>; response: { content: string; model: string; provider: string } }> {
  return apiJson(`/api/ai/prompts/${id}/dry-run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
