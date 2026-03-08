import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoPlay, IoShuffle, IoEllipsisVertical } from 'react-icons/io5';
import { useToast } from '../contexts/ToastContext';
import './Radio.css';

interface SintoniaRule {
  kind: 'include' | 'exclude';
  type: 'content_type' | 'genre' | 'artist' | 'tag';
  value: string;
}

interface Sintonia {
  id: number;
  name: string;
  created_at?: string;
  cover_path?: string | null;
  rules?: { kind: string; type: string; value: string }[];
}

interface RadioTrack {
  id: number;
  source?: string;
  file_index?: number;
  file_name?: string;
  item_name?: string;
  artist?: string;
}

const CONTENT_TYPES = [
  { value: 'music', label: 'Música' },
  { value: 'movies', label: 'Filmes' },
  { value: 'tv', label: 'Séries' },
];

function shuffleArray<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function Radio() {
  const [sintonias, setSintonias] = useState<Sintonia[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [displayTracks, setDisplayTracks] = useState<RadioTrack[]>([]);
  const [tracksLoading, setTracksLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formName, setFormName] = useState('');
  const [formRules, setFormRules] = useState<SintoniaRule[]>([]);
  const [saving, setSaving] = useState(false);
  const [uploadingCover, setUploadingCover] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [editCoverPath, setEditCoverPath] = useState<string | null>(null);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const coverInputRef = useRef<HTMLInputElement>(null);
  const optionsRef = useRef<HTMLDivElement>(null);
  const { showToast } = useToast();
  const navigate = useNavigate();

  const selectedSintonia = sintonias.find((s) => s.id === selectedId) ?? null;
  const mountedRef = useRef(true);
  useEffect(() => () => { mountedRef.current = false; }, []);

  const fetchSintonias = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      const res = await fetch('/api/radio/sintonias', { signal });
      if (signal?.aborted) return;
      const body = await res.text();
      if (signal?.aborted) return;
      if (!res.ok) {
        let detail = body;
        try {
          const j = JSON.parse(body);
          if (typeof j?.detail === 'string') detail = j.detail;
        } catch {
          /* */
        }
        throw new Error(detail);
      }
      const data = JSON.parse(body);
      const list = Array.isArray(data) ? data : [];
      setSintonias(list);
      if (list.length > 0 && selectedId === null) setSelectedId(list[0].id);
      else if (list.length > 0 && !list.some((s: Sintonia) => s.id === selectedId))
        setSelectedId(list[0].id);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      if (!mountedRef.current) return;
      setSintonias([]);
      showToast(err instanceof Error ? err.message : 'Não foi possível carregar as sintonias.', 5000);
    } finally {
      if (mountedRef.current && !signal?.aborted) setLoading(false);
    }
  }, [showToast, selectedId]);

  useEffect(() => {
    const controller = new AbortController();
    fetchSintonias(controller.signal);
    return () => controller.abort();
  }, [fetchSintonias]);

  const fetchQueue = useCallback(async (sintoniaId: number, signal?: AbortSignal) => {
    setTracksLoading(true);
    try {
      const res = await fetch(`/api/radio/sintonias/${sintoniaId}/queue?limit=100`, { method: 'POST', signal });
      if (signal?.aborted) return;
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (signal?.aborted) return;
      const list = data?.tracks ?? [];
      setDisplayTracks(list);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      if (!mountedRef.current) return;
      setDisplayTracks([]);
      showToast(err instanceof Error ? err.message : 'Não foi possível carregar a fila.', 4000);
    } finally {
      if (mountedRef.current && !signal?.aborted) setTracksLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    if (selectedId == null) { setDisplayTracks([]); return; }
    const controller = new AbortController();
    fetchQueue(selectedId, controller.signal);
    return () => controller.abort();
  }, [selectedId, fetchQueue]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (optionsRef.current && !optionsRef.current.contains(e.target as Node)) { setOptionsOpen(false); setConfirmDeleteId(null); }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setFormName('');
    setFormRules([]);
    setModalOpen(true);
  };

  const openEdit = async (s: Sintonia) => {
    setOptionsOpen(false);
    try {
      const res = await fetch(`/api/radio/sintonias/${s.id}`);
      if (!res.ok) throw new Error(await res.text());
      const full = (await res.json()) as Sintonia;
      setEditingId(full.id);
      setFormName(full.name || '');
      setEditCoverPath(full.cover_path ?? null);
      const rules: SintoniaRule[] = (full.rules || []).map((r) => ({
        kind: (r.kind === 'exclude' ? 'exclude' : 'include') as 'include' | 'exclude',
        type: (r.type as SintoniaRule['type']) || 'content_type',
        value: typeof r.value === 'string' ? r.value : JSON.stringify(r.value),
      }));
      setFormRules(rules);
      setModalOpen(true);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Não foi possível carregar a sintonia.', 4000);
    }
  };

  const uploadCover = async (sintoniaId: number, file: File) => {
    setUploadingCover(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`/api/radio/sintonias/${sintoniaId}/cover`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setEditCoverPath(data.cover_path ?? null);
      fetchSintonias();
      showToast('Capa atualizada.');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao enviar capa.', 4000);
    } finally {
      setUploadingCover(false);
    }
  };

  const addRule = (kind: 'include' | 'exclude') => {
    setFormRules((prev) => [...prev, { kind, type: 'content_type', value: 'music' }]);
  };

  const updateRule = (index: number, field: keyof SintoniaRule, value: string | SintoniaRule['type']) => {
    setFormRules((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const removeRule = (index: number) => {
    setFormRules((prev) => prev.filter((_, i) => i !== index));
  };

  const saveSintonia = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = formName.trim();
    if (!name) {
      showToast('Digite um nome para a sintonia.', 3000);
      return;
    }
    setSaving(true);
    const rules = formRules
      .map((r) => ({
        kind: r.kind,
        type: r.type,
        value: r.type === 'content_type' ? r.value : r.value.trim() || '',
      }))
      .filter((r) => r.type === 'content_type' || r.value);
    try {
      if (editingId != null) {
        const res = await fetch(`/api/radio/sintonias/${editingId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, rules }),
        });
        if (!res.ok) throw new Error(await res.text());
        showToast('Sintonia atualizada.');
      } else {
        const res = await fetch('/api/radio/sintonias', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, rules }),
        });
        if (!res.ok) throw new Error(await res.text());
        showToast('Sintonia criada.');
      }
      setModalOpen(false);
      fetchSintonias();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao salvar.', 4000);
    } finally {
      setSaving(false);
    }
  };

  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const deleteSintonia = async (id: number) => {
    if (confirmDeleteId !== id) {
      setConfirmDeleteId(id);
      return;
    }
    setConfirmDeleteId(null);
    setOptionsOpen(false);
    try {
      const res = await fetch(`/api/radio/sintonias/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(await res.text());
      showToast('Sintonia excluída.');
      if (selectedId === id) {
        const rest = sintonias.filter((s) => s.id !== id);
        setSelectedId(rest.length > 0 ? rest[0].id : null);
      }
      fetchSintonias();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao excluir.', 4000);
    }
  };

  const handlePlay = () => {
    if (displayTracks.length === 0) {
      showToast('Nenhuma faixa nesta sintonia.', 4000);
      return;
    }
    setPlaying(true);
    const first = displayTracks[0];
    const src = first.source || 'download';
    const fileParam = first.file_index != null ? `&file=${first.file_index}` : '';
    navigate(`/play-receiver/${first.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: { radioQueue: displayTracks, radioQueueIndex: 0 },
    });
    setPlaying(false);
  };

  const handleShuffle = () => {
    setDisplayTracks(shuffleArray(displayTracks));
    showToast('Ordem embaralhada.');
  };

  const playTrackAt = (index: number) => {
    if (index < 0 || index >= displayTracks.length) return;
    const t = displayTracks[index];
    const src = t.source || 'download';
    const fileParam = t.file_index != null ? `&file=${t.file_index}` : '';
    navigate(`/play-receiver/${t.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: { radioQueue: displayTracks, radioQueueIndex: index },
    });
  };

  const renderModal = () => (
    <>
      <div className="atum-radio-modal-backdrop" aria-hidden onClick={() => setModalOpen(false)} />
      <div className="atum-radio-modal" role="dialog" aria-label={editingId != null ? 'Editar sintonia' : 'Nova sintonia'}>
        <h2 className="atum-radio-modal-title">{editingId != null ? 'Editar sintonia' : 'Nova sintonia'}</h2>
        <form onSubmit={saveSintonia}>
          <label className="atum-radio-modal-label">
            Nome
            <input
              type="text"
              className="atum-radio-modal-input"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="Ex.: Só rock"
            />
          </label>
          {editingId != null && (
            <div className="atum-radio-modal-cover">
              <span className="atum-radio-modal-label">Capa</span>
              <div className="atum-radio-modal-cover-row">
                {editCoverPath ? (
                  <img src={`/api/radio/cover/${editingId}`} alt="Capa atual" className="atum-radio-modal-cover-preview" />
                ) : (
                  <div className="atum-radio-modal-cover-placeholder" aria-hidden>Sem capa</div>
                )}
                <div>
                  <input
                    ref={coverInputRef}
                    type="file"
                    accept="image/*"
                    className="atum-radio-modal-cover-input-hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f && editingId != null) uploadCover(editingId, f);
                      e.target.value = '';
                    }}
                    aria-label="Enviar nova capa"
                  />
                  <button
                    type="button"
                    className="atum-radio-btn"
                    onClick={() => coverInputRef.current?.click()}
                    disabled={uploadingCover}
                  >
                    {uploadingCover ? 'Enviando…' : 'Alterar capa'}
                  </button>
                </div>
              </div>
            </div>
          )}
          <div className="atum-radio-modal-rules">
            <p className="atum-radio-modal-rules-label">Regras (incluir ou excluir por tipo, gênero, artista, tag)</p>
            {formRules.map((r, i) => (
              <div key={i} className="atum-radio-modal-rule">
                <select
                  value={r.kind}
                  onChange={(e) => updateRule(i, 'kind', e.target.value as 'include' | 'exclude')}
                  className="atum-radio-modal-rule-kind"
                >
                  <option value="include">Incluir</option>
                  <option value="exclude">Excluir</option>
                </select>
                <select
                  value={r.type}
                  onChange={(e) => updateRule(i, 'type', e.target.value as SintoniaRule['type'])}
                  className="atum-radio-modal-rule-type"
                >
                  <option value="content_type">Tipo</option>
                  <option value="genre">Gênero</option>
                  <option value="artist">Artista</option>
                  <option value="tag">Tag</option>
                </select>
                {r.type === 'content_type' ? (
                  <select
                    value={r.value}
                    onChange={(e) => updateRule(i, 'value', e.target.value)}
                    className="atum-radio-modal-rule-value"
                  >
                    {CONTENT_TYPES.map((ct) => (
                      <option key={ct.value} value={ct.value}>{ct.label}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    className="atum-radio-modal-rule-value"
                    value={r.value}
                    onChange={(e) => updateRule(i, 'value', e.target.value)}
                    placeholder={r.type === 'genre' ? 'Ex.: Rock' : r.type === 'artist' ? 'Nome do artista' : 'Tag'}
                  />
                )}
                <button type="button" className="atum-radio-modal-rule-remove" onClick={() => removeRule(i)} aria-label="Remover regra">
                  ×
                </button>
              </div>
            ))}
            <div className="atum-radio-modal-rule-buttons">
              <button type="button" className="atum-radio-modal-add-rule" onClick={() => addRule('include')}>+ Incluir</button>
              <button type="button" className="atum-radio-modal-add-rule" onClick={() => addRule('exclude')}>+ Excluir</button>
            </div>
          </div>
          <div className="atum-radio-modal-actions">
            <button type="button" className="atum-radio-btn" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button type="submit" className="atum-radio-btn atum-radio-btn-play" disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </>
  );

  if (loading) {
    return (
      <div className="atum-radio atum-radio-playlist-layout">
        <div className="atum-radio-hero">
          <div className="atum-radio-hero-cover-wrap">
            <div className="atum-radio-hero-cover atum-radio-hero-cover-placeholder" aria-hidden>Rádio</div>
          </div>
          <div className="atum-radio-hero-text">
            <span className="atum-radio-hero-badge">Sintonia</span>
            <h1 className="atum-radio-hero-title">Carregando…</h1>
            <p className="atum-radio-hero-meta">—</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="atum-radio atum-radio-playlist-layout">
      {/* Hero Layer: Playlist Cover, Title, Metadata */}
      <div className="atum-radio-hero">
        <div className="atum-radio-hero-cover-wrap">
          {selectedSintonia?.cover_path ? (
            <img
              src={`/api/radio/cover/${selectedSintonia.id}`}
              alt=""
              className="atum-radio-hero-cover"
            />
          ) : (
            <div className="atum-radio-hero-cover atum-radio-hero-cover-placeholder" aria-hidden>
              Rádio
            </div>
          )}
        </div>
        <div className="atum-radio-hero-text">
          <span className="atum-radio-hero-badge">Sintonia</span>
          <h1 className="atum-radio-hero-title">
            {selectedSintonia?.name ?? (sintonias.length === 0 ? 'Nenhuma sintonia' : '—')}
          </h1>
          <p className="atum-radio-hero-meta">
            {sintonias.length === 0
              ? 'Crie uma sintonia para começar'
              : tracksLoading
                ? 'Carregando…'
                : `${displayTracks.length} faixa${displayTracks.length !== 1 ? 's' : ''}`}
          </p>
        </div>
      </div>

      <div className="atum-radio-controls">
        <button
          type="button"
          className="atum-radio-hero-btn atum-radio-hero-btn-primary"
          onClick={handlePlay}
          disabled={tracksLoading || displayTracks.length === 0 || playing}
          aria-label="Tocar"
        >
          <IoPlay size={28} />
          Tocar
        </button>
        <button
          type="button"
          className="atum-radio-hero-btn atum-radio-hero-btn-secondary"
          onClick={handleShuffle}
          disabled={tracksLoading || displayTracks.length === 0}
          aria-label="Embaralhar"
        >
          <IoShuffle size={22} />
          Embaralhar
        </button>
        {selectedSintonia && (
        <div className="atum-radio-options-wrap" ref={optionsRef}>
          <button
            type="button"
            className="atum-radio-hero-btn atum-radio-hero-btn-icon"
            onClick={() => setOptionsOpen((o) => !o)}
            aria-label="Opções"
            aria-expanded={optionsOpen}
          >
            <IoEllipsisVertical size={24} />
          </button>
          {optionsOpen && (
            <div className="atum-radio-options-menu">
              <button type="button" className="atum-radio-options-item" onClick={() => openEdit(selectedSintonia)}>
                Editar sintonia
              </button>
              <button type="button" className="atum-radio-options-item atum-radio-options-item-danger" onClick={() => selectedSintonia && deleteSintonia(selectedSintonia.id)}>
                {confirmDeleteId === selectedSintonia?.id ? 'Confirmar exclusão?' : 'Excluir'}
              </button>
            </div>
          )}
        </div>
        )}
      </div>

      <div className="atum-radio-select-wrap">
        <label htmlFor="atum-radio-select" className="atum-radio-select-label">Sintonia</label>
        {sintonias.length > 0 ? (
          <select
            id="atum-radio-select"
            className="atum-radio-select"
            value={selectedId ?? ''}
            onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          >
            {sintonias.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        ) : null}
        <button type="button" className="atum-radio-new-link" onClick={openCreate}>
          + Nova sintonia
        </button>
      </div>

      <div className="atum-radio-content">
        <div className="atum-radio-tracks-wrap">
          {sintonias.length === 0 ? (
            <div className="atum-radio-tracks-empty-state">
              <p className="atum-radio-tracks-empty">Crie uma sintonia para começar (ex.: só música, só rock, sem filmes).</p>
              <button type="button" className="atum-radio-hero-btn atum-radio-hero-btn-primary" onClick={openCreate}>
                Nova sintonia
              </button>
            </div>
          ) : tracksLoading ? (
            <p className="atum-radio-tracks-loading">Carregando faixas…</p>
          ) : displayTracks.length === 0 ? (
            <p className="atum-radio-tracks-empty">Nenhuma faixa corresponde a esta sintonia.</p>
          ) : (
            <table className="atum-radio-tracks-table" aria-label="Faixas">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Título</th>
                  <th scope="col">Álbum</th>
                </tr>
              </thead>
              <tbody>
                {displayTracks.map((t, i) => (
                  <tr
                    key={`${t.id}-${t.file_index ?? 0}-${i}`}
                    className="atum-radio-track-row"
                    role="button"
                    tabIndex={0}
                    onClick={() => playTrackAt(i)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        playTrackAt(i);
                      }
                    }}
                  >
                    <td className="atum-radio-track-num">{i + 1}</td>
                    <td className="atum-radio-track-title-cell">
                      <span className="atum-radio-track-title">{t.file_name || t.item_name || '—'}</span>
                      {t.artist && <span className="atum-radio-track-artist">{t.artist}</span>}
                    </td>
                    <td className="atum-radio-track-album">{t.item_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {modalOpen && renderModal()}
    </div>
  );
}
