/**
 * API de Chat AI — conversa contextual, streaming e Smart Queue.
 */
import { apiJson } from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatContext {
  track?: string;
  artist?: string;
  album?: string;
  codec?: string;
  bitrate?: string;
  volume?: number;
  bass?: number;
  mid?: number;
  treble?: number;
}

export interface ChatRequest {
  messages: ChatMessage[];
  context?: ChatContext;
}

export interface ChatResponse {
  content: string;
  model?: string;
  provider?: string;
}

export interface SmartQueueRequest {
  prompt: string;
  library_items?: Array<{
    id?: number;
    name?: string;
    artist?: string;
    genre?: string;
    moods?: string[];
    sub_genres?: string[];
    bpm?: number;
  }>;
}

export interface SmartQueueResponse {
  ids: number[];
  explanation: string;
}

export async function chat(
  body: ChatRequest,
  options?: { signal?: AbortSignal }
): Promise<ChatResponse> {
  return apiJson<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options?.signal,
  });
}

/**
 * Retorna a Response bruta para streaming. O caller deve usar res.body?.getReader().
 */
export async function chatStream(
  body: ChatRequest,
  options?: { signal?: AbortSignal }
): Promise<Response> {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options?.signal,
  });
  return res;
}

export async function chatQueue(body: SmartQueueRequest): Promise<SmartQueueResponse> {
  return apiJson<SmartQueueResponse>('/api/chat/queue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
