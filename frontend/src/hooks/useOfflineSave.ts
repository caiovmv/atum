import { useCallback, useState } from 'react';
import { getLibraryItemFiles, type LibraryFile } from '../api/library';
import { saveStreamsToDirectory } from '../utils/fileSystemAccess';

export interface UseOfflineSaveParams {
  itemId: number;
  isImport: boolean;
  onSuccess?: (saved: number, total: number) => void;
  onError?: (message: string) => void;
}

export function useOfflineSave({
  itemId,
  isImport,
  onSuccess,
  onError,
}: UseOfflineSaveParams) {
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number; filename: string } | null>(null);

  const save = useCallback(async () => {
    setSaving(true);
    setProgress(null);
    try {
      const { files } = await getLibraryItemFiles(itemId, isImport);
      if (!files.length) {
        onError?.('Nenhum arquivo encontrado.');
        return;
      }

      const baseUrl = isImport ? `/api/library/imported/${itemId}` : `/api/library/${itemId}`;
      const entries = files.map((f: LibraryFile) => ({
        streamUrl: `${baseUrl}/stream?file_index=${f.index}`,
        filename: f.name || `track-${f.index}.mp3`,
      }));

      const result = await saveStreamsToDirectory(entries, (idx, total, filename) => {
        setProgress({ current: idx, total, filename });
      });

      setProgress(null);
      if (result.saved > 0) {
        onSuccess?.(result.saved, result.saved + result.failed);
      }
      if (result.failed > 0 && result.errors?.length) {
        onError?.(result.errors.join('; '));
      }
      if (result.saved === 0 && result.failed > 0) {
        onError?.(result.errors?.[0] ?? 'Falha ao salvar.');
      }
    } catch (err) {
      setProgress(null);
      onError?.(err instanceof Error ? err.message : 'Erro ao salvar.');
    } finally {
      setSaving(false);
    }
  }, [itemId, isImport, onSuccess, onError]);

  return { save, saving, progress };
}
