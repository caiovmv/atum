import type { RuleForm } from '../../hooks/usePlaylists';

const CONTENT_TYPES = [
  { value: 'music', label: 'Música' },
  { value: 'movies', label: 'Filmes' },
  { value: 'tv', label: 'Séries' },
];

interface PlaylistCreateFormProps {
  createMode: 'static' | 'dynamic_rules' | 'dynamic_ai';
  setCreateMode: (m: 'static' | 'dynamic_rules' | 'dynamic_ai') => void;
  newName: string;
  setNewName: (v: string) => void;
  newDescription: string;
  setNewDescription: (v: string) => void;
  newRules: RuleForm[];
  setNewRules: React.Dispatch<React.SetStateAction<RuleForm[]>>;
  newPrompt: string;
  setNewPrompt: (v: string) => void;
  onCreate: () => void;
  onCancel: () => void;
  addRule: (kind: 'include' | 'exclude') => void;
}

export function PlaylistCreateForm({
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
  onCreate,
  onCancel,
  addRule,
}: PlaylistCreateFormProps) {
  return (
    <div className="playlists-create-form">
      <div className="playlists-create-mode-tabs">
        {[
          { value: 'static' as const, label: 'Playlist' },
          { value: 'dynamic_rules' as const, label: 'Sintonia' },
          { value: 'dynamic_ai' as const, label: 'AI Mix' },
        ].map((m) => (
          <button
            key={m.value}
            type="button"
            className={`playlists-create-mode-tab${createMode === m.value ? ' playlists-create-mode-tab--active' : ''}`}
            onClick={() => setCreateMode(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <input
        type="text"
        className="playlists-create-input"
        placeholder="Nome da coleção…"
        value={newName}
        onChange={(e) => setNewName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onCreate();
          if (e.key === 'Escape') onCancel();
        }}
        autoFocus
      />

      <input
        type="text"
        className="playlists-create-input"
        placeholder="Descrição (opcional)…"
        value={newDescription}
        onChange={(e) => setNewDescription(e.target.value)}
      />

      {createMode === 'dynamic_rules' && (
        <div className="playlists-create-rules">
          <p className="playlists-create-rules-label">Regras de filtragem</p>
          {newRules.map((r, i) => (
            <div key={i} className="playlists-create-rule">
              <select
                value={r.kind}
                onChange={(e) =>
                  setNewRules((prev) => {
                    const next = [...prev];
                    next[i] = { ...next[i], kind: e.target.value as 'include' | 'exclude' };
                    return next;
                  })
                }
              >
                <option value="include">Incluir</option>
                <option value="exclude">Excluir</option>
              </select>
              <select
                value={r.type}
                onChange={(e) =>
                  setNewRules((prev) => {
                    const next = [...prev];
                    next[i] = { ...next[i], type: e.target.value as RuleForm['type'] };
                    return next;
                  })
                }
              >
                <option value="content_type">Tipo</option>
                <option value="genre">Gênero</option>
                <option value="artist">Artista</option>
                <option value="tag">Tag</option>
              </select>
              {r.type === 'content_type' ? (
                <select
                  value={r.value}
                  onChange={(e) =>
                    setNewRules((prev) => {
                      const next = [...prev];
                      next[i] = { ...next[i], value: e.target.value };
                      return next;
                    })
                  }
                >
                  {CONTENT_TYPES.map((ct) => (
                    <option key={ct.value} value={ct.value}>
                      {ct.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  placeholder={
                    r.type === 'genre' ? 'Ex.: Rock' : r.type === 'artist' ? 'Artista' : 'Tag'
                  }
                  value={r.value}
                  onChange={(e) =>
                    setNewRules((prev) => {
                      const next = [...prev];
                      next[i] = { ...next[i], value: e.target.value };
                      return next;
                    })
                  }
                />
              )}
              <button
                type="button"
                onClick={() => setNewRules((prev) => prev.filter((_, j) => j !== i))}
              >
                ×
              </button>
            </div>
          ))}
          <div className="playlists-create-rule-btns">
            <button type="button" onClick={() => addRule('include')}>
              + Incluir
            </button>
            <button type="button" onClick={() => addRule('exclude')}>
              + Excluir
            </button>
          </div>
        </div>
      )}

      {createMode === 'dynamic_ai' && (
        <textarea
          className="playlists-create-prompt"
          placeholder="Descreva o que você quer ouvir... Ex.: Jazz suave para estudar, Rock energético para malhar"
          value={newPrompt}
          onChange={(e) => setNewPrompt(e.target.value)}
          rows={3}
        />
      )}

      <div className="playlists-create-actions">
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          onClick={onCreate}
          disabled={!newName.trim()}
        >
          Criar
        </button>
        <button type="button" className="atum-btn" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
