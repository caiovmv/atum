import { Toggle, Field } from './SettingsForm';

interface TestResult {
  ok: boolean;
  message?: string;
  error?: string;
}

interface IntegrationsSectionProps {
  val: (key: string) => string;
  set: (key: string, value: unknown) => void;
  boolVal: (key: string) => boolean;
  testResults: Record<string, TestResult>;
  testing: Record<string, boolean>;
  onTestConnection: (service: string, params: Record<string, string>) => void;
}

export function IntegrationsSection({
  val,
  set,
  boolVal,
  testResults,
  testing,
  onTestConnection,
}: IntegrationsSectionProps) {
  return (
    <section className="atum-settings-section">
      <h2 className="atum-settings-section-title">Integrações</h2>
      <div className="atum-settings-group">
        {/* TMDB */}
        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">TMDB (The Movie Database)</span>
            {testResults.tmdb && (
              <span className={`atum-settings-integration-status atum-settings-integration-status--${testResults.tmdb.ok ? 'ok' : 'error'}`}>
                {testResults.tmdb.ok ? 'Conectado' : 'Erro'}
              </span>
            )}
          </div>
          <div className="atum-settings-group">
            <Field
              label="API Key"
              hint="Obtenha em themoviedb.org/settings/api"
              type="password"
              value={val('tmdb_api_key')}
              onChange={(v) => set('tmdb_api_key', v)}
              placeholder="Sua TMDB API Key"
            />
            <div className="atum-settings-field-row">
              <button
                type="button"
                className="atum-btn"
                disabled={testing.tmdb}
                onClick={() => onTestConnection('tmdb', { api_key: val('tmdb_api_key') })}
              >
                {testing.tmdb ? 'Testando...' : 'Testar Conexão'}
              </button>
            </div>
            {testResults.tmdb && (
              <div className={`atum-settings-test-result atum-settings-test-result--${testResults.tmdb.ok ? 'ok' : 'error'}`}>
                {testResults.tmdb.ok ? testResults.tmdb.message : testResults.tmdb.error}
              </div>
            )}
          </div>
        </div>

        {/* Plex */}
        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">Plex Media Server</span>
            {testResults.plex && (
              <span className={`atum-settings-integration-status atum-settings-integration-status--${testResults.plex.ok ? 'ok' : 'error'}`}>
                {testResults.plex.ok ? 'Conectado' : 'Erro'}
              </span>
            )}
          </div>
          <div className="atum-settings-group">
            <Field
              label="URL do servidor"
              hint="Ex: http://localhost:32400"
              value={val('plex_url')}
              onChange={(v) => set('plex_url', v)}
              placeholder="http://localhost:32400"
            />
            <Field
              label="Token"
              hint="Token de autenticação do Plex"
              type="password"
              value={val('plex_token')}
              onChange={(v) => set('plex_token', v)}
              placeholder="Plex Token"
            />
            <Field
              label="IDs das seções"
              hint="IDs das bibliotecas Plex para scan automático (separados por vírgula)"
              value={val('plex_section_ids')}
              onChange={(v) => set('plex_section_ids', v)}
              placeholder="1,2,3"
            />
            <Toggle
              label="Scan automático"
              hint="Disparar scan da biblioteca Plex após organizar novo conteúdo"
              checked={boolVal('plex_auto_scan')}
              onChange={(v) => set('plex_auto_scan', v)}
            />
            <div className="atum-settings-field-row">
              <button
                type="button"
                className="atum-btn"
                disabled={testing.plex}
                onClick={() => onTestConnection('plex', { url: val('plex_url'), token: val('plex_token') })}
              >
                {testing.plex ? 'Testando...' : 'Testar Conexão'}
              </button>
            </div>
            {testResults.plex && (
              <div className={`atum-settings-test-result atum-settings-test-result--${testResults.plex.ok ? 'ok' : 'error'}`}>
                {testResults.plex.ok ? testResults.plex.message : testResults.plex.error}
              </div>
            )}
          </div>
        </div>

        {/* Jellyfin */}
        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">Jellyfin</span>
            {testResults.jellyfin && (
              <span className={`atum-settings-integration-status atum-settings-integration-status--${testResults.jellyfin.ok ? 'ok' : 'error'}`}>
                {testResults.jellyfin.ok ? 'Conectado' : 'Erro'}
              </span>
            )}
          </div>
          <div className="atum-settings-group">
            <Field
              label="URL do servidor"
              hint="Ex: http://localhost:8096"
              value={val('jellyfin_url')}
              onChange={(v) => set('jellyfin_url', v)}
              placeholder="http://localhost:8096"
            />
            <Field
              label="API Key"
              hint="Token de autenticação do Jellyfin"
              type="password"
              value={val('jellyfin_api_key')}
              onChange={(v) => set('jellyfin_api_key', v)}
              placeholder="Jellyfin API Key"
            />
            <Toggle
              label="Scan automático"
              hint="Disparar scan da biblioteca Jellyfin após organizar novo conteúdo"
              checked={boolVal('jellyfin_auto_scan')}
              onChange={(v) => set('jellyfin_auto_scan', v)}
            />
            <div className="atum-settings-field-row">
              <button
                type="button"
                className="atum-btn"
                disabled={testing.jellyfin}
                onClick={() => onTestConnection('jellyfin', { url: val('jellyfin_url'), api_key: val('jellyfin_api_key') })}
              >
                {testing.jellyfin ? 'Testando...' : 'Testar Conexão'}
              </button>
            </div>
            {testResults.jellyfin && (
              <div className={`atum-settings-test-result atum-settings-test-result--${testResults.jellyfin.ok ? 'ok' : 'error'}`}>
                {testResults.jellyfin.ok ? testResults.jellyfin.message : testResults.jellyfin.error}
              </div>
            )}
          </div>
        </div>

        {/* Last.fm */}
        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">Last.fm</span>
          </div>
          <div className="atum-settings-group">
            <Field
              label="API Key"
              hint="Obtenha em last.fm/api/account"
              type="password"
              value={val('lastfm_api_key')}
              onChange={(v) => set('lastfm_api_key', v)}
              placeholder="Sua Last.fm API Key"
            />
          </div>
        </div>

        {/* Spotify */}
        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">Spotify</span>
          </div>
          <div className="atum-settings-group">
            <Field
              label="Client ID"
              hint="Obtenha em developer.spotify.com/dashboard"
              value={val('spotify_client_id')}
              onChange={(v) => set('spotify_client_id', v)}
              placeholder="Spotify Client ID"
            />
            <Field
              label="Client Secret"
              type="password"
              value={val('spotify_client_secret')}
              onChange={(v) => set('spotify_client_secret', v)}
              placeholder="Spotify Client Secret"
            />
            <div className="atum-settings-notice">
              Para o enriquecimento de música usar Audio Features do Spotify, é necessário autenticar via CLI:
              <code>dl-torrent spotify login</code>. Sem isso, essa fonte é ignorada automaticamente.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
