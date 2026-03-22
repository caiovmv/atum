/**
 * Testes para ShakaPlayer.
 *
 * Estratégia de mock:
 * - fetch global é mockado para controlar respostas do backend HLS.
 * - shaka-player é mockado com um Player mínimo.
 * - Fake timers são usados LOCALMENTE apenas nos testes de polling (202 + status).
 *
 * Nota de design: o <video> permanece sempre no DOM (exceto no estado "fallback"),
 * garantindo que videoRef.current esteja disponível para o Shaka se anexar.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ShakaPlayer } from '../ShakaPlayer';

// ── Mock do shaka-player ────────────────────────────────────────────────────

const mockLoad = vi.fn().mockResolvedValue(undefined);
const mockAttach = vi.fn().mockResolvedValue(undefined);
const mockDestroy = vi.fn().mockResolvedValue(undefined);
const mockAddEventListener = vi.fn();

vi.mock('shaka-player', () => ({
  default: {
    polyfill: { installAll: vi.fn() },
    Player: class MockPlayer {
      static isBrowserSupported() { return true; }
      attach = mockAttach;
      load = mockLoad;
      destroy = mockDestroy;
      addEventListener = mockAddEventListener;
    },
  },
}));

// ── Constantes ────────────────────────────────────────────────────────────────

const HLS_URL = '/api/library/1/hls/0/master.m3u8';
const FALLBACK_URL = '/api/library/1/stream?file_index=0';

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  mockLoad.mockClear();
  mockAttach.mockClear();
  mockDestroy.mockClear();
  mockAddEventListener.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockFetch(hlsStatus: number) {
  return vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
    if (opts?.method === 'DELETE') {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
    }
    const status = String(url).includes('master.m3u8') ? hlsStatus : 200;
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve({}),
    });
  });
}

// ── Testes ────────────────────────────────────────────────────────────────────

describe('ShakaPlayer', () => {
  describe('estado "ready" (HLS disponível imediatamente)', () => {
    it('inicializa Shaka Player quando master.m3u8 retorna 200', async () => {
      vi.stubGlobal('fetch', mockFetch(200));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => {
        expect(mockAttach).toHaveBeenCalled();
        expect(mockLoad).toHaveBeenCalledWith(HLS_URL);
      }, { timeout: 3000 });
    });

    it('não exibe overlay de processamento quando Shaka carrega normalmente', async () => {
      vi.stubGlobal('fetch', mockFetch(200));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => expect(mockLoad).toHaveBeenCalled(), { timeout: 3000 });

      expect(document.querySelector('.shaka-processing-overlay')).toBeNull();
    });

    it('renderiza <video> sem src (Shaka controla a mídia)', async () => {
      vi.stubGlobal('fetch', mockFetch(200));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => expect(mockLoad).toHaveBeenCalled(), { timeout: 3000 });

      const video = document.querySelector('video');
      expect(video).not.toBeNull();
      expect(video?.getAttribute('src')).toBeNull();
    });
  });

  describe('estado "processing" (202 Accepted — FFmpeg em andamento)', () => {
    it('exibe overlay com "Preparando vídeo" quando backend retorna 202', async () => {
      vi.stubGlobal('fetch', mockFetch(202));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => {
        expect(screen.getByText(/Preparando vídeo/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('<video> permanece no DOM mesmo durante o overlay de processamento', async () => {
      vi.stubGlobal('fetch', mockFetch(202));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => {
        expect(screen.getByText(/Preparando vídeo/i)).toBeInTheDocument();
      }, { timeout: 3000 });

      // Garantia central: o <video> deve estar no DOM para Shaka se anexar depois
      expect(document.querySelector('video')).not.toBeNull();
    });

    it('exibe botões de ação no estado processing', async () => {
      vi.stubGlobal('fetch', mockFetch(202));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => {
        expect(screen.getByText(/Reproduzir agora/i)).toBeInTheDocument();
        expect(screen.getByText(/Reiniciar transcodificação/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    it('exibe progresso % após polling do status', async () => {
      vi.useFakeTimers();
      try {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
          if (String(url).includes('master.m3u8')) {
            return Promise.resolve({ ok: false, status: 202, json: () => Promise.resolve({}) });
          }
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve({ status: 'processing', progress: 42 }),
          });
        }));

        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);

        await act(async () => { await vi.advanceTimersByTimeAsync(3100); });

        expect(screen.getByText(/42%/)).toBeInTheDocument();
      } finally {
        vi.useRealTimers();
      }
    });

    it('barra de progresso exibe fill proporcional ao % recebido', async () => {
      vi.useFakeTimers();
      try {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
          if (String(url).includes('master.m3u8')) {
            return Promise.resolve({ ok: false, status: 202, json: () => Promise.resolve({}) });
          }
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve({ status: 'processing', progress: 75 }),
          });
        }));

        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);

        await act(async () => { await vi.advanceTimersByTimeAsync(3100); });

        const fill = document.querySelector('.shaka-progress-fill') as HTMLElement | null;
        expect(fill).not.toBeNull();
        expect(fill?.style.width).toBe('75%');
      } finally {
        vi.useRealTimers();
      }
    });

    it('inicia Shaka quando polling retorna status=ready', async () => {
      vi.useFakeTimers();
      try {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
          if (String(url).includes('master.m3u8')) {
            return Promise.resolve({ ok: false, status: 202, json: () => Promise.resolve({}) });
          }
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve({ status: 'ready', progress: 100 }),
          });
        }));

        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);

        // runAllTimersAsync dispara o setTimeout de polling e aguarda todas as
        // Promises encadeadas (pollStatus → initShaka → attach → load)
        await act(async () => { await vi.runAllTimersAsync(); });

        expect(mockLoad).toHaveBeenCalledWith(HLS_URL);
      } finally {
        vi.useRealTimers();
      }
    });

    it('exibe mensagem de erro quando polling retorna status=error', async () => {
      vi.useFakeTimers();
      try {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
          if (String(url).includes('master.m3u8')) {
            return Promise.resolve({ ok: false, status: 202, json: () => Promise.resolve({}) });
          }
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve({ status: 'error', error_message: 'FFmpeg falhou' }),
          });
        }));

        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);

        await act(async () => { await vi.advanceTimersByTimeAsync(3100); });

        expect(screen.getByText(/FFmpeg falhou/)).toBeInTheDocument();
      } finally {
        vi.useRealTimers();
      }
    });

    it('botão "Reiniciar" envia DELETE para o endpoint HLS', async () => {
      const fetchMock = mockFetch(202);
      vi.stubGlobal('fetch', fetchMock);

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => screen.getByText(/Reiniciar transcodificação/i), { timeout: 3000 });

      await act(async () => {
        fireEvent.click(screen.getByText(/Reiniciar transcodificação/i));
      });

      const deleteCalls = (fetchMock.mock.calls as [string, RequestInit | undefined][]).filter(
        ([, opts]) => opts?.method === 'DELETE',
      );
      expect(deleteCalls.length).toBeGreaterThan(0);
    });
  });

  describe('estado "fallback"', () => {
    it('renderiza <video> com src do fallback quando HLS retorna 500', async () => {
      vi.stubGlobal('fetch', mockFetch(500));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => {
        const video = document.querySelector('video');
        expect(video).not.toBeNull();
        expect(video?.src).toContain('stream');
      }, { timeout: 3000 });
    });

    it('botão "Reproduzir agora" exibe vídeo fallback ao clicar', async () => {
      vi.stubGlobal('fetch', mockFetch(202));

      await act(async () => {
        render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);
      });

      await waitFor(() => screen.getByText(/Reproduzir agora/i), { timeout: 3000 });

      await act(async () => {
        fireEvent.click(screen.getByText(/Reproduzir agora/i));
      });

      // Após fallback, o <video> deve ter src apontando para o fallback
      await waitFor(() => {
        const video = document.querySelector('video');
        expect(video?.src).toContain('stream');
      }, { timeout: 2000 });
    });
  });

  describe('limpeza (unmount)', () => {
    it('chama player.destroy() ao desmontar o componente', async () => {
      vi.stubGlobal('fetch', mockFetch(200));

      const { unmount } = render(<ShakaPlayer hlsUrl={HLS_URL} fallbackUrl={FALLBACK_URL} />);

      await waitFor(() => expect(mockLoad).toHaveBeenCalled(), { timeout: 3000 });

      unmount();
      expect(mockDestroy).toHaveBeenCalled();
    });
  });
});
