import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { useFetch } from './useFetch';
import {
  getPlaylist,
  updatePlaylist,
  deletePlaylist as apiDeletePlaylist,
  removeTrackFromPlaylist,
  uploadPlaylistCover,
  generatePlaylist,
} from '../api/playlists';

export function usePlaylistDetail(id: string | undefined) {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { data: playlist, loading, error: fetchError, refetch } = useFetch(
    (signal) => (id ? getPlaylist(id, { signal }) : Promise.resolve(null)),
    [id ?? '']
  );

  const [downloadOpen, setDownloadOpen] = useState(false);
  const [selectedSize, setSelectedSize] = useState(16);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editPrompt, setEditPrompt] = useState('');
  const [regenerating, setRegenerating] = useState(false);

  const playAll = useCallback(() => {
    if (!playlist || playlist.tracks.length === 0) return;
    const queue = playlist.tracks.map((t) => ({
      id: t.item_id,
      source: t.source,
      file_index: t.file_index,
      file_name: t.file_name || t.item_name || '—',
      item_name: t.item_name,
      artist: t.artist,
    }));
    const first = queue[0];
    navigate(`/play-receiver/${first.id}?source=${first.source}`, {
      state: { radioQueue: queue, radioQueueIndex: 0 },
    });
  }, [playlist, navigate]);

  const playTrack = useCallback(
    (index: number) => {
      if (!playlist) return;
      const queue = playlist.tracks.map((t) => ({
        id: t.item_id,
        source: t.source,
        file_index: t.file_index,
        file_name: t.file_name || t.item_name || '—',
        item_name: t.item_name,
        artist: t.artist,
      }));
      const target = queue[index];
      navigate(`/play-receiver/${target.id}?source=${target.source}`, {
        state: { radioQueue: queue, radioQueueIndex: index },
      });
    },
    [playlist, navigate]
  );

  const removeTrack = useCallback(
    async (trackId: number) => {
      if (!playlist) return;
      try {
        await removeTrackFromPlaylist(playlist.id, trackId);
        refetch();
      } catch {
        showToast('Erro ao remover faixa');
      }
    },
    [playlist, refetch, showToast]
  );

  const deletePlaylist = useCallback(async () => {
    if (!playlist || playlist.system_kind) return;
    if (!window.confirm(`Excluir "${playlist.name}"?`)) return;
    try {
      await apiDeletePlaylist(playlist.id);
      showToast(`"${playlist.name}" excluída`);
      navigate('/playlists');
    } catch {
      showToast('Erro ao excluir');
    }
  }, [playlist, navigate, showToast]);

  const openEdit = useCallback(() => {
    if (!playlist) return;
    setEditName(playlist.name);
    setEditDescription(playlist.description || '');
    setEditPrompt(playlist.ai_prompt || '');
    setEditing(true);
  }, [playlist]);

  const handleSaveEdit = useCallback(async () => {
    if (!playlist || !editName.trim()) return;
    try {
      await updatePlaylist(playlist.id, {
        name: editName.trim(),
        ...(editDescription.trim() !== (playlist.description || '') && {
          description: editDescription.trim() || null,
        }),
        ...(playlist.kind === 'dynamic_ai' &&
          editPrompt.trim() !== (playlist.ai_prompt || '') && {
            ai_prompt: editPrompt.trim() || null,
          }),
      });
      setEditing(false);
      refetch();
      showToast('Coleção atualizada');
    } catch {
      showToast('Erro ao salvar');
    }
  }, [playlist, editName, editDescription, editPrompt, refetch, showToast]);

  const handleCoverUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!playlist?.id || !e.target.files?.[0]) return;
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) {
        showToast('Arquivo muito grande (máx 5 MB)');
        e.target.value = '';
        return;
      }
      try {
        await uploadPlaylistCover(playlist.id, file);
        showToast('Capa atualizada');
        refetch();
      } catch (err) {
        showToast(err instanceof Error ? err.message : 'Erro ao enviar capa');
      }
      e.target.value = '';
    },
    [playlist, refetch, showToast]
  );

  const handleRegenerate = useCallback(async () => {
    if (!playlist) return;
    setRegenerating(true);
    try {
      await generatePlaylist(playlist.id);
      showToast('Coleção regenerada');
      refetch();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao regenerar');
    } finally {
      setRegenerating(false);
    }
  }, [playlist, refetch, showToast]);

  return {
    playlist,
    loading,
    fetchError,
    downloadOpen,
    setDownloadOpen,
    selectedSize,
    setSelectedSize,
    editing,
    setEditing,
    editName,
    setEditName,
    editDescription,
    setEditDescription,
    editPrompt,
    setEditPrompt,
    regenerating,
    playAll,
    playTrack,
    removeTrack,
    deletePlaylist,
    openEdit,
    handleSaveEdit,
    handleCoverUpload,
    handleRegenerate,
    navigate,
  };
}
