export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes < 1024 * 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  return `${(bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2)} TB`;
}

const STATUS_LABELS: Record<string, string> = {
  queued: 'Enfileirado',
  downloading: 'Baixando',
  paused: 'Pausado',
  completed: 'Concluído',
  failed: 'Falhou',
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}
