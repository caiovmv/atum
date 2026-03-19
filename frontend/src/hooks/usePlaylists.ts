import { useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { useFetch } from './useFetch';
import { getPlaylists, createPlaylist, generatePlaylist } from '../api/playlists';

export type TabKind = 'all' | 'static' | 'dynamic_rules' | 'dynamic_ai';

export interface RuleForm {
  kind: 'include' | 'exclude';
  type: 'content_type' | 'genre' | 'artist' | 'tag';
  value: string;
}

export type CreateMode = 'static' | 'dynamic_rules' | 'dynamic_ai';

export function usePlaylists() {
  const [creating, setCreating] = useState(false);
  const [createMode, setCreateMode] = useState<CreateMode>('static');
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newRules, setNewRules] = useState<RuleForm[]>([]);
  const [newPrompt, setNewPrompt] = useState('');
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const activeTab = (searchParams.get('kind') as TabKind) || 'all';

  const { data: playlistsData, loading, error: fetchError, refetch } = useFetch(
    (signal) => getPlaylists(activeTab !== 'all' ? activeTab : undefined, { signal }),
    [activeTab]
  );
  const playlists = playlistsData ?? [];

  const handleTabChange = useCallback(
    (tab: TabKind) => {
      if (tab === 'all') {
        setSearchParams({});
      } else {
        setSearchParams({ kind: tab });
      }
    },
    [setSearchParams]
  );

  const addRule = useCallback((kind: 'include' | 'exclude') => {
    setNewRules((prev) => [...prev, { kind, type: 'content_type', value: 'music' }]);
  }, []);

  const handleCreate = useCallback(async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      const body = {
        name,
        kind: createMode,
        ...(newDescription.trim() && { description: newDescription.trim() }),
        ...(createMode === 'dynamic_rules' &&
          newRules.length > 0 && {
            rules: newRules.filter((r) => r.type === 'content_type' || r.value.trim()),
          }),
        ...(createMode === 'dynamic_ai' && newPrompt.trim() && { ai_prompt: newPrompt.trim() }),
      };
      const created = await createPlaylist(body);
      const id = created?.id;
      if (createMode === 'dynamic_ai' && id) {
        try {
          const gen = await generatePlaylist(id);
          const count = gen.count ?? gen.tracks?.length ?? 0;
          showToast(`AI Mix "${name}" criada com ${count} faixa(s)`);
        } catch {
          showToast(`AI Mix "${name}" criada (clique em Regenerar para gerar faixas)`);
        }
      } else {
        const kindLabel =
          createMode === 'dynamic_rules' ? 'Sintonia' : createMode === 'dynamic_ai' ? 'AI Mix' : 'Playlist';
        showToast(`${kindLabel} "${name}" criada`);
      }
      setNewName('');
      setNewDescription('');
      setNewRules([]);
      setNewPrompt('');
      refetch();
      if (createMode === 'dynamic_ai' && id) {
        navigate(`/playlists/${id}`);
      }
    } catch {
      showToast('Erro ao criar');
    } finally {
      setCreating(false);
    }
  }, [
    newName,
    newDescription,
    newRules,
    newPrompt,
    createMode,
    showToast,
    refetch,
    navigate,
  ]);

  const resetCreateForm = useCallback(() => {
    setCreating(false);
    setNewName('');
    setNewDescription('');
    setNewRules([]);
    setNewPrompt('');
  }, []);

  return {
    creating,
    setCreating,
    createMode,
    setCreateMode,
    newName,
    setNewName,
    newDescription,
    setNewDescription,
    newRules,
    setNewRules,
    newPrompt,
    setNewPrompt,
    activeTab,
    playlists,
    loading,
    fetchError,
    refetch,
    handleTabChange,
    handleCreate,
    addRule,
    resetCreateForm,
  };
}
