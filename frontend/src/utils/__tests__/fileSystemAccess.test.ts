import { describe, it, expect, vi, afterEach } from 'vitest';
import { hasFileSystemAccessSupport, saveStreamsToDirectory } from '../fileSystemAccess';

describe('fileSystemAccess', () => {
  const originalWindow = globalThis.window;

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(globalThis, 'window', {
      value: originalWindow,
      writable: true,
    });
  });

  describe('hasFileSystemAccessSupport', () => {
    it('returns false when window is undefined', () => {
      const win = globalThis.window;
      Object.defineProperty(globalThis, 'window', { value: undefined, writable: true });
      expect(hasFileSystemAccessSupport()).toBe(false);
      Object.defineProperty(globalThis, 'window', { value: win, writable: true });
    });

    it('returns false when showDirectoryPicker is not in window', () => {
      const win = { ...originalWindow };
      delete (win as Record<string, unknown>)['showDirectoryPicker'];
      vi.stubGlobal('window', win);
      expect(hasFileSystemAccessSupport()).toBe(false);
    });

    it('returns true when showDirectoryPicker exists', () => {
      vi.stubGlobal('window', { ...originalWindow, showDirectoryPicker: vi.fn() });
      expect(hasFileSystemAccessSupport()).toBe(true);
    });
  });

  describe('saveStreamsToDirectory', () => {
    it('returns error when browser does not support File System Access', async () => {
      vi.stubGlobal('window', {});
      const result = await saveStreamsToDirectory([
        { streamUrl: '/api/stream/1', filename: 'track.mp3' },
      ]);
      expect(result).toEqual({
        ok: false,
        saved: 0,
        failed: 1,
        errors: ['Navegador não suporta acesso a pastas.'],
      });
    });

    it('returns user cancelled when showDirectoryPicker throws AbortError', async () => {
      const err = new Error('User cancelled');
      (err as Error & { name: string }).name = 'AbortError';
      vi.stubGlobal('window', {
        showDirectoryPicker: vi.fn().mockRejectedValue(err),
      });
      const result = await saveStreamsToDirectory([
        { streamUrl: '/api/stream/1', filename: 'track.mp3' },
      ]);
      expect(result).toEqual({
        ok: false,
        saved: 0,
        failed: 0,
        errors: ['Usuário cancelou.'],
      });
    });
  });
});
