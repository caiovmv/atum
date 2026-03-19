import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useOfflineSave } from '../useOfflineSave';
import * as libraryApi from '../../api/library';
import * as fileSystemAccess from '../../utils/fileSystemAccess';

vi.mock('../../api/library');
vi.mock('../../utils/fileSystemAccess');

describe('useOfflineSave', () => {
  const mockOnSuccess = vi.fn();
  const mockOnError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fileSystemAccess.hasFileSystemAccessSupport).mockReturnValue(true);
    vi.mocked(libraryApi.getLibraryItemFiles).mockResolvedValue({
      files: [
        { index: 0, name: 'track1.mp3', size: 1024 },
        { index: 1, name: 'track2.mp3', size: 2048 },
      ],
    });
    vi.mocked(fileSystemAccess.saveStreamsToDirectory).mockResolvedValue({
      ok: true,
      saved: 2,
      failed: 0,
    });
  });

  it('calls getLibraryItemFiles and saveStreamsToDirectory on save', async () => {
    const { result } = renderHook(() =>
      useOfflineSave({
        itemId: 42,
        isImport: false,
        onSuccess: mockOnSuccess,
        onError: mockOnError,
      })
    );

    await act(async () => {
      result.current.save();
    });

    expect(libraryApi.getLibraryItemFiles).toHaveBeenCalledWith(42, false);
    expect(fileSystemAccess.saveStreamsToDirectory).toHaveBeenCalledWith(
      [
        { streamUrl: '/api/library/42/stream?file_index=0', filename: 'track1.mp3' },
        { streamUrl: '/api/library/42/stream?file_index=1', filename: 'track2.mp3' },
      ],
      expect.any(Function)
    );
    expect(mockOnSuccess).toHaveBeenCalledWith(2, 2);
    expect(mockOnError).not.toHaveBeenCalled();
  });

  it('uses imported stream URL when isImport is true', async () => {
    const { result } = renderHook(() =>
      useOfflineSave({
        itemId: 10,
        isImport: true,
        onSuccess: mockOnSuccess,
        onError: mockOnError,
      })
    );

    await act(async () => {
      result.current.save();
    });

    expect(fileSystemAccess.saveStreamsToDirectory).toHaveBeenCalledWith(
      [
        { streamUrl: '/api/library/imported/10/stream?file_index=0', filename: 'track1.mp3' },
        { streamUrl: '/api/library/imported/10/stream?file_index=1', filename: 'track2.mp3' },
      ],
      expect.any(Function)
    );
  });

  it('calls onError when no files are found', async () => {
    vi.mocked(libraryApi.getLibraryItemFiles).mockResolvedValue({ files: [] });

    const { result } = renderHook(() =>
      useOfflineSave({
        itemId: 1,
        isImport: false,
        onSuccess: mockOnSuccess,
        onError: mockOnError,
      })
    );

    await act(async () => {
      result.current.save();
    });

    expect(mockOnError).toHaveBeenCalledWith('Nenhum arquivo encontrado.');
    expect(mockOnSuccess).not.toHaveBeenCalled();
    expect(fileSystemAccess.saveStreamsToDirectory).not.toHaveBeenCalled();
  });

  it('calls onError when saveStreamsToDirectory fails', async () => {
    vi.mocked(fileSystemAccess.saveStreamsToDirectory).mockResolvedValue({
      ok: false,
      saved: 0,
      failed: 2,
      errors: ['Erro ao salvar.'],
    });

    const { result } = renderHook(() =>
      useOfflineSave({
        itemId: 1,
        isImport: false,
        onSuccess: mockOnSuccess,
        onError: mockOnError,
      })
    );

    await act(async () => {
      result.current.save();
    });

    expect(mockOnError).toHaveBeenCalledWith('Erro ao salvar.');
  });
});
