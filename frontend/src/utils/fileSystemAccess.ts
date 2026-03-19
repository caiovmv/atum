/**
 * File System Access API — salvar arquivos em pasta escolhida pelo usuário.
 * Suportado em Chrome/Chromium (incluindo Android TWA).
 * Permite gravar músicas em pasta real, visível no gerenciador de arquivos.
 */

export function hasFileSystemAccessSupport(): boolean {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

export interface SaveResult {
  ok: boolean;
  saved: number;
  failed: number;
  errors?: string[];
}

/**
 * Salva um ou mais streams em arquivos na pasta escolhida pelo usuário.
 * @param entries Array de { streamUrl, filename }
 * @param onProgress Callback opcional (index, total, filename) durante o download
 */
export async function saveStreamsToDirectory(
  entries: Array<{ streamUrl: string; filename: string }>,
  onProgress?: (index: number, total: number, filename: string) => void
): Promise<SaveResult> {
  if (!hasFileSystemAccessSupport()) {
    return { ok: false, saved: 0, failed: entries.length, errors: ['Navegador não suporta acesso a pastas.'] };
  }

  let dir: FileSystemDirectoryHandle;
  try {
    dir = await window.showDirectoryPicker!({ mode: 'readwrite' });
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      return { ok: false, saved: 0, failed: 0, errors: ['Usuário cancelou.'] };
    }
    return {
      ok: false,
      saved: 0,
      failed: entries.length,
      errors: [err instanceof Error ? err.message : 'Erro ao abrir pasta.'],
    };
  }

  const total = entries.length;
  let saved = 0;
  const errors: string[] = [];

  for (let i = 0; i < entries.length; i++) {
    const { streamUrl, filename } = entries[i];
    onProgress?.(i + 1, total, filename);
    try {
      const res = await fetch(streamUrl);
      if (!res.ok) {
        errors.push(`${filename}: HTTP ${res.status}`);
        continue;
      }
      const blob = await res.blob();
      const safeName = sanitizeFilename(filename) || `file-${i + 1}`;
      const fileHandle = await dir.getFileHandle(safeName, { create: true });
      const writable = await fileHandle.createWritable();
      await writable.write(blob);
      await writable.close();
      saved++;
    } catch (err) {
      errors.push(`${filename}: ${err instanceof Error ? err.message : 'Erro desconhecido'}`);
    }
  }

  return {
    ok: saved > 0,
    saved,
    failed: total - saved,
    errors: errors.length > 0 ? errors : undefined,
  };
}

function sanitizeFilename(name: string): string {
  return name
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 200) || 'arquivo';
}
