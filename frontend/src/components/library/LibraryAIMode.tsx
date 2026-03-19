import { useState, useCallback } from 'react';
import { BottomSheet } from '../BottomSheet';
import { chatQueue } from '../../api/chat';
import type { LibraryItem } from '../../types/library';
import './LibraryAIMode.css';

const QUICK_SUGGESTIONS = [
  'Relaxante',
  'Energético',
  'Nostálgico',
  'Rock anos 80',
  'Jazz para trabalhar',
  'Música para festa',
];

interface LibraryAIModeProps {
  open: boolean;
  onClose: () => void;
  items: LibraryItem[];
  onAiResults: (ids: number[], explanation: string) => void;
}

export function LibraryAIMode({
  open,
  onClose,
  items,
  onAiResults,
}: LibraryAIModeProps) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async () => {
    const p = prompt.trim();
    if (!p) return;
    setError(null);
    setLoading(true);
    try {
      const libItems = items.slice(0, 50).map((it, idx) => ({
        id: idx,
        name: it.name,
        artist: it.artist,
        genre: it.genre,
        moods: (it as { moods?: string[] }).moods,
        sub_genres: (it as { sub_genres?: string[] }).sub_genres,
        bpm: (it as { bpm?: number }).bpm,
      }));
      const data = await chatQueue({ prompt: p, library_items: libItems });
      onAiResults(data.ids || [], data.explanation || '');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar.');
    } finally {
      setLoading(false);
    }
  }, [prompt, items, onAiResults, onClose]);

  const handleSuggestion = (s: string) => {
    setPrompt(s);
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Modo AI" showCloseButton>
      <div className="atum-library-ai">
        <p className="atum-library-ai-hint">
          Descreva o que procura em linguagem natural. A IA seleciona itens da sua biblioteca que combinam.
        </p>
        <div className="atum-library-ai-form">
          <label>
            O que você quer ouvir?
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex: música relaxante para trabalhar"
              onKeyDown={(e) => e.key === 'Enter' && runSearch()}
              disabled={loading}
            />
          </label>
        </div>
        <div className="atum-library-ai-suggestions">
          <span className="atum-library-ai-suggestions-label">Sugestões:</span>
          {QUICK_SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className="atum-btn atum-btn-ghost atum-library-ai-chip"
              onClick={() => handleSuggestion(s)}
              disabled={loading}
            >
              {s}
            </button>
          ))}
        </div>
        {error && (
          <p className="atum-library-ai-error" role="alert">
            {error}
          </p>
        )}
        <div className="atum-library-ai-actions">
          <button type="button" className="atum-btn" onClick={onClose}>
            Fechar
          </button>
          <button
            type="button"
            className="atum-btn atum-btn-primary"
            onClick={runSearch}
            disabled={loading || !prompt.trim()}
          >
            {loading ? 'Buscando…' : 'Buscar'}
          </button>
        </div>
      </div>
    </BottomSheet>
  );
}
