/**
 * Declarações de tipo mínimas para shaka-player 4.x.
 *
 * O shaka-player é distribuído sem tipos oficiais no npm.
 * Este módulo declara apenas a superfície de API usada pelo ShakaPlayer.tsx.
 * Ao atualizar a versão do shaka-player, revise se novos métodos precisam ser
 * declarados aqui.
 *
 * Referência: https://shaka-player-demo.appspot.com/docs/api/shaka.Player.html
 */

declare module 'shaka-player' {
  namespace shaka {
    namespace polyfill {
      /** Instala todos os polyfills necessários (MSE, EME, etc.). Chamar antes de usar Player. */
      function installAll(): void;
    }

    /** Evento de erro emitido pelo Player. */
    interface ShakaErrorEvent {
      detail: {
        code: number;
        category: number;
        severity: number;
        message: string;
      };
    }

    /** Configuração de DRM (Phase 3). */
    interface DrmConfiguration {
      servers: Record<string, string>;
      advanced?: Record<string, unknown>;
    }

    /** Configuração completa do player (subconjunto usado atualmente). */
    interface PlayerConfiguration {
      drm?: DrmConfiguration;
      streaming?: {
        bufferingGoal?: number;
        rebufferingGoal?: number;
        retryParameters?: {
          maxAttempts?: number;
          baseDelay?: number;
        };
      };
    }

    class Player {
      /** Verifica se o navegador tem suporte a MSE/EME suficiente para o Shaka. */
      static isBrowserSupported(): boolean;

      /** Conecta o Player a um elemento <video> existente. */
      attach(video: HTMLVideoElement): Promise<void>;

      /** Carrega um manifesto HLS ou DASH pela URL. */
      load(assetUri: string, startTime?: number): Promise<void>;

      /** Destrói o player e libera recursos. Sempre chamar ao desmontar o componente. */
      destroy(): Promise<void>;

      /** Configura opções do player (streaming, DRM, etc.). */
      configure(config: Partial<PlayerConfiguration>): void;

      /** Registra um listener de evento do player. */
      addEventListener(
        type: 'error',
        listener: (event: ShakaErrorEvent) => void,
      ): void;
      addEventListener(type: string, listener: (event: unknown) => void): void;

      /** Remove um listener de evento. */
      removeEventListener(type: string, listener: (event: unknown) => void): void;
    }
  }

  /** Export padrão do módulo shaka-player. */
  const defaultExport: {
    polyfill: typeof shaka.polyfill;
    Player: typeof shaka.Player;
  };

  export = defaultExport;
}
