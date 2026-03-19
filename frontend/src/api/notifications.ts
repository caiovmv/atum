import { apiGet, apiJson, evictCache } from './client';

export { evictCache };

export interface Notification {
  id: number;
  type?: string;
  title?: string;
  body?: string;
  payload?: Record<string, unknown>;
  read?: boolean;
  created_at?: string;
  [key: string]: unknown;
}

export async function getUnreadCount(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<number> {
  const data = await apiGet<{ count?: number }>('/api/notifications/unread-count', { staleMs: 15_000, ...options });
  return data?.count ?? 0;
}

export async function getNotifications(
  limit = 30,
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<Notification[]> {
  const data = await apiGet<Notification[]>(`/api/notifications?limit=${limit}`, { staleMs: 10_000, ...options });
  return Array.isArray(data) ? data : [];
}

export async function markNotificationRead(id: number): Promise<void> {
  await apiJson<unknown>(`/api/notifications/${id}/read`, { method: 'PATCH' });
  evictCache('/api/notifications');
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiJson<unknown>('/api/notifications/mark-all-read', { method: 'POST' });
  evictCache('/api/notifications');
}

export async function clearNotifications(): Promise<void> {
  await apiJson<unknown>('/api/notifications/clear', { method: 'POST' });
}
