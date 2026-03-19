import { useState, useCallback, useRef, useEffect } from 'react';
import { getLibrary } from '../api/library';
import { createPlaylist, generatePlaylist } from '../api/playlists';
import { chat, chatStream, chatQueue } from '../api/chat';
import type { EQSuggestion, SmartQueueResult, AgentAction } from '../components/receiver/ReceiverAI';
import { parseAction } from '../components/receiver/ReceiverAI';

export interface ChatMsg {
  role: 'user' | 'assistant';
  content: string;
  isStep?: boolean;
}

interface UseReceiverAIProps {
  trackTitle?: string;
  artist?: string;
  album?: string;
  codec?: string;
  bitrate?: string;
  volume?: number;
  bass?: number;
  mid?: number;
  treble?: number;
  onApplyEQ?: (eq: EQSuggestion) => void;
  onSmartQueue?: (result: SmartQueueResult) => void;
  onAction?: (action: AgentAction) => void;
}

export function useReceiverAI({
  trackTitle,
  artist,
  album,
  codec,
  bitrate,
  volume: currentVolume,
  bass: currentBass,
  mid: currentMid,
  treble: currentTreble,
  onApplyEQ,
  onSmartQueue,
  onAction,
}: UseReceiverAIProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const streamAbortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasSpeech = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  const toggleVoice = useCallback(() => {
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      setListening(false);
      return;
    }
    const SR = window.SpeechRecognition || (window as unknown as { webkitSpeechRecognition: typeof SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = 'pt-BR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (ev: SpeechRecognitionEvent) => {
      const transcript = ev.results[0]?.[0]?.transcript;
      if (transcript) setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    rec.onend = () => setListening(false);
    rec.onerror = (ev: Event) => {
      setListening(false);
      const errType = (ev as { error?: string }).error;
      if (errType === 'not-allowed') setError('Microfone não permitido');
      else if (errType === 'no-speech') setError('Nenhuma fala detectada');
      else if (errType === 'audio-capture') setError('Microfone não disponível');
    };
    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }, [listening]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }
      streamAbortRef.current?.abort();
    };
  }, []);

  const runCreateCollection = useCallback(
    (ac: Extract<AgentAction, { action: 'create_collection' }>, setMsgs: React.Dispatch<React.SetStateAction<ChatMsg[]>>) => {
      const addStep = (msg: string) => setMsgs((m) => [...m, { role: 'assistant' as const, content: msg, isStep: true }]);
      (async () => {
        try {
          addStep(`Criando coleção "${ac.name}"…`);
          const created = await createPlaylist({
            name: ac.name,
            kind: ac.kind || 'static',
            rules: ac.rules,
            ai_prompt: ac.ai_prompt,
            description: ac.description,
          });
          const id = created.id;
          addStep(`Coleção criada.`);
          if (ac.kind === 'dynamic_ai' && id) {
            addStep(`Regenerando faixas com o prompt…`);
            try {
              const gen = await generatePlaylist(id);
              const count = gen.count ?? (Array.isArray(gen.tracks) ? gen.tracks.length : 0);
              addStep(`Coleção pronta com ${count} faixa(s).`);
            } catch (genErr) {
              addStep(`Erro ao regenerar: ${genErr instanceof Error ? genErr.message : 'Erro'}`);
            }
          }
          if (id) onAction?.({ action: 'navigate', path: `/playlists/${id}` });
        } catch (e) {
          addStep(`Erro: ${e instanceof Error ? e.message : 'Erro desconhecido'}`);
        }
      })();
    },
    [onAction]
  );

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    setError(null);

    const userMsg: ChatMsg = { role: 'user', content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setLoading(true);

    try {
      streamAbortRef.current?.abort();
      const ctrl = new AbortController();
      streamAbortRef.current = ctrl;
      const res = await chatStream(
        {
          messages: newMessages.map((m) => ({ role: m.role, content: m.content })),
          context: {
            track: trackTitle,
            artist,
            album,
            codec,
            bitrate,
            volume: currentVolume,
            bass: currentBass,
            mid: currentMid,
            treble: currentTreble,
          },
        },
        { signal: ctrl.signal }
      );

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(data.detail || `Erro ${res.status}`);
      }

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('event: done')) break;
            if (line.startsWith('event: error')) continue;
            if (line.startsWith('data: ')) {
              const chunk = line.slice(6);
              if (chunk === '[DONE]') break;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, content: last.content + chunk };
                }
                return updated;
              });
            }
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant' && last.content) {
          const { clean, action } = parseAction(last.content);
          if (action?.action === 'create_collection' && 'name' in action && action.name) {
            const updated = [...prev];
            updated[updated.length - 1] = { ...last, content: clean };
            queueMicrotask(() => runCreateCollection(action, setMessages));
            return updated;
          }
          if (action) {
            onAction?.(action);
            const updated = [...prev];
            updated[updated.length - 1] = { ...last, content: clean };
            return updated;
          }
        }
        return prev;
      });
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [
    input,
    loading,
    messages,
    trackTitle,
    artist,
    album,
    codec,
    bitrate,
    currentVolume,
    currentBass,
    currentMid,
    currentTreble,
    onAction,
    runCreateCollection,
  ]);

  const requestSmartQueue = useCallback(
    async (prompt: string) => {
      if (loading || !onSmartQueue) return;
      setError(null);
      setMessages((prev) => [...prev, { role: 'user', content: prompt }]);
      setLoading(true);
      try {
        const libItems = await getLibrary({}, { staleMs: 30_000 }).catch(() => []);
        const items = libItems.slice(0, 50).map((i) => ({
          id: i.id,
          name: i.name,
          artist: i.artist,
          genre: i.genre,
          moods: (i as { moods?: string[] }).moods ?? i.tags,
          sub_genres: (i as { sub_genres?: string[] }).sub_genres,
          bpm: (i as { bpm?: number }).bpm,
        }));

        const data = await chatQueue({ prompt, library_items: items });
        if (data.ids?.length > 0) {
          onSmartQueue({ ids: data.ids, explanation: data.explanation || '' });
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `Fila montada com ${data.ids.length} faixa(s). ${data.explanation}`,
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.explanation || 'Não encontrei faixas que combinem.',
            },
          ]);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Erro');
      } finally {
        setLoading(false);
      }
    },
    [loading, onSmartQueue]
  );

  const requestEQ = useCallback(async () => {
    if (loading || !onApplyEQ) return;
    setError(null);
    const codecCtx = codec ? ` (codec: ${codec}${bitrate ? `, ${bitrate}` : ''})` : '';
    const prompt = `Analise o gênero/estilo de "${trackTitle || 'esta faixa'}"${artist ? ` de ${artist}` : ''}${album ? ` (álbum: ${album})` : ''}${codecCtx} e sugira EQ otimizada. Considere: 1) Características do gênero 2) Se lossy, evite boost >3dB em agudos 3) Volume atual ${currentVolume ?? 80}%. Responda SOMENTE com JSON puro (sem markdown): {"bass": N, "mid": N, "treble": N} onde N é inteiro de -6 a 6.`;
    const userMsg: ChatMsg = { role: 'user', content: 'Aplicar Auto-EQ' };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const data = await chat({
        messages: [{ role: 'user', content: prompt }],
        context: {
          track: trackTitle,
          artist,
          album,
          codec,
          bitrate,
          volume: currentVolume,
          bass: currentBass,
          mid: currentMid,
          treble: currentTreble,
        },
      });
      const text = data.content || '';
      const jsonMatch = text.match(/\{[^}]*"bass"[^}]*\}/i);
      if (jsonMatch) {
        const eq = JSON.parse(jsonMatch[0]) as Record<string, number>;
        const clamp = (v: number) => Math.max(-6, Math.min(6, Math.round(v)));
        const suggestion: EQSuggestion = {
          bass: clamp(eq.bass ?? 0),
          mid: clamp(eq.mid ?? 0),
          treble: clamp(eq.treble ?? 0),
        };
        onApplyEQ(suggestion);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `EQ aplicada: Bass ${suggestion.bass > 0 ? '+' : ''}${suggestion.bass} · Mid ${suggestion.mid > 0 ? '+' : ''}${suggestion.mid} · Treble ${suggestion.treble > 0 ? '+' : ''}${suggestion.treble}`,
          },
        ]);
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: text }]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro');
    } finally {
      setLoading(false);
    }
  }, [
    loading,
    onApplyEQ,
    trackTitle,
    artist,
    album,
    codec,
    bitrate,
    currentVolume,
    currentBass,
    currentMid,
    currentTreble,
  ]);

  return {
    messages,
    input,
    setInput,
    loading,
    error,
    listening,
    hasSpeech,
    inputRef,
    send,
    toggleVoice,
    requestSmartQueue,
    requestEQ,
  };
}
