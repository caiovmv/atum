/**
 * ShakaPlayer — wrapper React para Shaka Player com suporte a HLS adaptativo.
 *
 * Fluxo:
 * 1. Verifica status do HLS via polling em /hls/{fileIndex}/status
 * 2. Enquanto FFmpeg processa, exibe spinner "Preparando vídeo..."
 * 3. Quando pronto, inicializa shaka.Player e carrega master.m3u8
 * 4. Em caso de erro de transcodificação ou inicialização, cai de volta
 *    para o stream progressivo direto (fallbackUrl)
 *
 * Phase 2/3: para DRM, configurar player.configure({ drm: { servers: {...} } })
 * antes de chamar player.load().
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import './ShakaPlayer.css';

// Shaka Player exporta via CommonJS; usamos dynamic import para compatibilidade
// com Vite (tree-shaking não se aplica aqui — a lib tem ~1.5 MB, carregar lazy
// quando o player é renderizado é mais eficiente).
async function loadShaka() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mod = await import('shaka-player');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (mod.default ?? mod) as any;
}

type PlayerStatus = 'idle' | 'checking' | 'processing' | 'loading' | 'ready' | 'fallback';

export interface ShakaPlayerProps {
  /** URL do manifest HLS master (ex: /api/library/1/hls/0/master.m3u8) */
  hlsUrl: string;
  /** URL de stream progressivo — usado como fallback se HLS falhar */
  fallbackUrl: string;
  className?: string;
  autoPlay?: boolean;
  controls?: boolean;
  onVideoRef?: (el: HTMLVideoElement | null) => void;
}

export function ShakaPlayer({
  hlsUrl,
  fallbackUrl,
  className,
  autoPlay = true,
  controls = true,
  onVideoRef,
}: ShakaPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const playerRef = useRef<any>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const [status, setStatus] = useState<PlayerStatus>('idle');
  const [processingMsg, setProcessingMsg] = useState('Preparando vídeo…');
  const [progress, setProgress] = useState(0);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const statusUrl = hlsUrl.replace(/\/master\.m3u8$/, '/status');

  const clearPoll = useCallback(() => {
    if (pollTimerRef.current !== null) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const useFallback = useCallback((reason?: string) => {
    if (!mountedRef.current) return;
    clearPoll();
    if (reason) setErrorBanner(reason);
    setStatus('fallback');
  }, [clearPoll]);

  const initShaka = useCallback(async () => {
    if (!mountedRef.current || !videoRef.current) return;
    setStatus('loading');
    try {
      const shaka = await loadShaka();

      // Instala polyfills (necessário para Safari/MSE)
      shaka.polyfill.installAll();

      if (!shaka.Player.isBrowserSupported()) {
        useFallback('Navegador não suporta HLS adaptativo.');
        return;
      }

      const player = new shaka.Player();
      await player.attach(videoRef.current);
      playerRef.current = player;

      player.addEventListener('error', (event: { detail: { message: string } }) => {
        if (!mountedRef.current) return;
        useFallback(`Shaka: ${event.detail?.message ?? 'erro desconhecido'}`);
      });

      await player.load(hlsUrl);
      if (!mountedRef.current) return;
      setStatus('ready');
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      useFallback(`Falha ao carregar HLS: ${msg}`);
    }
  }, [hlsUrl, useFallback]);

  const pollStatus = useCallback(async () => {
    if (!mountedRef.current) return;
    try {
      const r = await fetch(statusUrl);
      if (!r.ok) { useFallback('Erro ao verificar status HLS.'); return; }
      const data: { status: string; error_message?: string } = await r.json();

      if (!mountedRef.current) return;

      if (data.status === 'ready') {
        clearPoll();
        setProgress(100);
        await initShaka();
        return;
      }

      if (data.status === 'error') {
        useFallback(data.error_message ?? 'Erro na transcodificação.');
        return;
      }

      // 'pending' | 'processing' — continua aguardando
      const pct = (data as { progress?: number }).progress ?? 0;
      setProgress(pct);
      setProcessingMsg(
        data.status === 'processing'
          ? pct > 0 ? `Transcodificando… ${pct}%` : 'Transcodificando vídeo…'
          : 'Preparando vídeo…'
      );
      pollTimerRef.current = setTimeout(pollStatus, 3000);
    } catch {
      if (mountedRef.current) {
        pollTimerRef.current = setTimeout(pollStatus, 5000);
      }
    }
  }, [statusUrl, clearPoll, initShaka, useFallback]);

  const start = useCallback(async () => {
    if (!mountedRef.current) return;
    setStatus('checking');

    try {
      // GET no master.m3u8 dispara a transcodificação backend e verifica se
      // reprodução progressiva já é possível (primeiro segmento disponível).
      const r = await fetch(hlsUrl, { method: 'GET' });

      if (!mountedRef.current) return;

      if (r.status === 200) {
        // Master manifest disponível: inicia Shaka em modo progressivo.
        // Se FFmpeg ainda está em andamento, as playlists de variante crescem
        // incrementalmente e o Shaka as re-busca automaticamente (live-like HLS).
        await initShaka();
        return;
      }

      if (r.status === 202) {
        // Segmentos ainda não disponíveis → polling até reprodução ser possível
        setStatus('processing');
        setProcessingMsg('Preparando vídeo…');
        pollTimerRef.current = setTimeout(pollStatus, 3000);
        return;
      }

      // Qualquer outro erro (400, 500, etc.) → fallback progressivo
      useFallback(`HLS indisponível (${r.status}).`);
    } catch {
      useFallback('Não foi possível conectar ao servidor HLS.');
    }
  }, [hlsUrl, initShaka, pollStatus, useFallback]);

  useEffect(() => {
    mountedRef.current = true;
    start();

    return () => {
      mountedRef.current = false;
      clearPoll();
      playerRef.current?.destroy().catch(() => {/* silencioso */});
      playerRef.current = null;
    };
    // hlsUrl muda quando o usuário troca de arquivo → reinicializa tudo
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hlsUrl]);

  useEffect(() => {
    onVideoRef?.(videoRef.current);
  }, [onVideoRef]);

  // ── Render ────────────────────────────────────────────────────────────────

  if (status === 'fallback') {
    return (
      <div className={`shaka-player-wrap ${className ?? ''}`.trim()}>
        <video
          ref={videoRef}
          src={fallbackUrl}
          controls={controls}
          autoPlay={autoPlay}
          playsInline
        />
        {errorBanner && <div className="shaka-error-banner">{errorBanner}</div>}
      </div>
    );
  }

  if (status === 'processing' || status === 'checking') {
    const retranscodeUrl = hlsUrl.replace(/\/master\.m3u8$/, '');
    return (
      <div className={`shaka-player-wrap ${className ?? ''}`.trim()}>
        <div className="shaka-processing">
          <div className="shaka-processing-spinner" />
          <p>{processingMsg}</p>
          {progress > 0 && (
            <div className="shaka-progress-bar" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
              <div className="shaka-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          )}
          <button
            type="button"
            className="shaka-retranscode-btn"
            title="Cancelar e reproduzir via stream direto"
            onClick={() => useFallback('Usando stream direto.')}
          >
            Reproduzir agora (sem HLS)
          </button>
          <button
            type="button"
            className="shaka-retranscode-btn shaka-retranscode-btn--secondary"
            title="Forçar re-transcodificação"
            onClick={async () => {
              try {
                await fetch(retranscodeUrl, { method: 'DELETE' });
              } catch { /* ignorar */ }
              setStatus('idle');
              setProgress(0);
              start();
            }}
          >
            Reiniciar transcodificação
          </button>
        </div>
      </div>
    );
  }

  // idle, loading, ready → renderiza o elemento <video> (Shaka vai se anexar a ele)
  return (
    <div className={`shaka-player-wrap ${className ?? ''}`.trim()}>
      <video
        ref={videoRef}
        controls={controls}
        autoPlay={autoPlay}
        playsInline
      />
      {errorBanner && <div className="shaka-error-banner">{errorBanner}</div>}
    </div>
  );
}
