import { useState, useEffect, useCallback } from 'react';
import './Settings.css';

interface SettingsData {
  [key: string]: unknown;
}

interface TestResult {
  ok: boolean;
  message?: string;
  error?: string;
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="atum-settings-toggle-wrap">
      <div className="atum-settings-toggle-info">
        <div className="atum-settings-label">{label}</div>
        {hint && <div className="atum-settings-hint">{hint}</div>}
      </div>
      <label className="atum-settings-toggle" aria-label={label}>
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
        <span className="atum-settings-toggle-track" />
      </label>
    </div>
  );
}

function Field({
  label,
  hint,
  type = 'text',
  value,
  onChange,
  placeholder,
  children,
}: {
  label: string;
  hint?: string;
  type?: string;
  value?: string;
  onChange?: (v: string) => void;
  placeholder?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="atum-settings-field">
      <span className="atum-settings-label">{label}</span>
      {hint && <span className="atum-settings-hint">{hint}</span>}
      {children ?? (
        <input
          type={type}
          className="atum-settings-input"
          value={value ?? ''}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
        />
      )}
    </div>
  );
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsData>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState<SettingsData>({});
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchSettings = useCallback(async (signal?: AbortSignal) => {
    setFetchError(null);
    try {
      const res = await fetch('/api/settings', { signal });
      if (signal?.aborted) return;
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      } else {
        setFetchError(`Erro ao carregar configurações (HTTP ${res.status})`);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setFetchError('Erro de conexão ao carregar configurações');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    setLoading(true);
    Promise.all([
      fetch('/api/settings', { signal }).then((r) => (r.ok ? r.json() : null)),
      fetch('/api/settings/enrichment-stats', { signal }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([settingsData, statsData]) => {
        if (signal.aborted) return;
        if (settingsData) setSettings(settingsData);
        else setFetchError('Erro ao carregar configurações');
        if (statsData) setEnrichmentStats(statsData);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setFetchError('Erro de conexão ao carregar configurações');
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const val = (key: string): string => {
    if (key in dirty) return String(dirty[key] ?? '');
    return String(settings[key] ?? '');
  };

  const boolVal = (key: string): boolean => {
    if (key in dirty) return Boolean(dirty[key]);
    return Boolean(settings[key]);
  };

  const set = (key: string, value: unknown) => {
    setDirty((prev) => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    if (Object.keys(dirty).length === 0) return;
    setSaving(true);
    try {
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: dirty }),
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setDirty({});
        setSaved(true);
        setTimeout(() => setSaved(false), 2500);
      }
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async (service: string, params: Record<string, string>) => {
    setTesting((prev) => ({ ...prev, [service]: true }));
    setTestResults((prev) => {
      const copy = { ...prev };
      delete copy[service];
      return copy;
    });
    try {
      const res = await fetch('/api/settings/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service, ...params }),
      });
      if (res.ok) {
        const data = await res.json();
        setTestResults((prev) => ({ ...prev, [service]: data }));
      }
    } catch {
      setTestResults((prev) => ({ ...prev, [service]: { ok: false, error: 'Erro de rede' } }));
    } finally {
      setTesting((prev) => ({ ...prev, [service]: false }));
    }
  };

  const [reorganizing, setReorganizing] = useState(false);
  const [reorganizeResult, setReorganizeResult] = useState<{
    processed: number;
    skipped: number;
    errors: number;
    dry_run: boolean;
    details: string[];
  } | null>(null);

  const reorganizeLibrary = async (dryRun: boolean) => {
    setReorganizing(true);
    setReorganizeResult(null);
    try {
      const params = new URLSearchParams();
      if (dryRun) params.set('dry_run', 'true');
      const res = await fetch(`/api/settings/reorganize-library?${params}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setReorganizeResult(data);
      }
    } catch {
      // ignore
    } finally {
      setReorganizing(false);
    }
  };

  const [enrichmentStats, setEnrichmentStats] = useState<{
    total: number; enriched: number; errors: number; pending: number;
  } | null>(null);


  const hasDirty = Object.keys(dirty).length > 0;

  if (loading) {
    return (
      <div className="atum-settings">
        <h1 className="atum-settings-title">Configurações</h1>
        <p className="atum-settings-desc">Carregando...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="atum-settings">
        <h1 className="atum-settings-title">Configurações</h1>
        <div className="atum-settings-test-result atum-settings-test-result--error" style={{ marginBottom: '1rem' }}>
          {fetchError}
        </div>
        <button type="button" className="atum-btn" onClick={() => { setLoading(true); fetchSettings(); }}>
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="atum-settings">
      <h1 className="atum-settings-title">Configurações</h1>
      <p className="atum-settings-desc">Gerencie configurações do sistema, organização e integrações.</p>

      {/* Geral */}
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Geral</h2>
        <div className="atum-settings-group">
          <Field
            label="Pasta de Música"
            hint="Caminho da pasta principal de música (LIBRARY_MUSIC_PATH)"
            value={val('library_music_path')}
            onChange={(v) => set('library_music_path', v)}
            placeholder="D:\Library\Music"
          />
          <Field
            label="Pasta de Vídeos"
            hint="Caminho da pasta principal de vídeos (LIBRARY_VIDEOS_PATH)"
            value={val('library_videos_path')}
            onChange={(v) => set('library_videos_path', v)}
            placeholder="D:\Library\Videos"
          />
        </div>
      </section>

      {/* Organização */}
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Organização</h2>
        <div className="atum-settings-group">
          <Toggle
            label="Pós-processamento automático"
            hint="Organizar arquivos automaticamente após o download concluir"
            checked={boolVal('post_process_enabled')}
            onChange={(v) => set('post_process_enabled', v)}
          />
          <Field label="Modo de organização" hint="Como os arquivos são organizados após o download">
            <select
              className="atum-settings-select"
              value={val('organize_mode') || 'in_place'}
              onChange={(e) => set('organize_mode', e.target.value)}
            >
              <option value="in_place">In-place (renomear na mesma pasta)</option>
              <option value="hardlink_to_library">Hardlink para biblioteca separada</option>
              <option value="copy_to_library">Copiar para biblioteca separada</option>
            </select>
          </Field>
          <Toggle
            label="Naming Plex-compatible"
            hint="Renomear arquivos seguindo convenção do Plex (ex: Movie (2010)/Movie (2010).mkv)"
            checked={boolVal('plex_naming_enabled')}
            onChange={(v) => set('plex_naming_enabled', v)}
          />
          <Toggle
            label="Incluir TMDB ID na pasta"
            hint="Adicionar {tmdb-12345} no nome da pasta para matching preciso"
            checked={boolVal('include_tmdb_id_in_folder')}
            onChange={(v) => set('include_tmdb_id_in_folder', v)}
          />
          <Toggle
            label="Incluir IMDB ID na pasta"
            hint="Adicionar {imdb-tt0137523} no nome da pasta"
            checked={boolVal('include_imdb_id_in_folder')}
            onChange={(v) => set('include_imdb_id_in_folder', v)}
          />
          <Toggle
            label="Upgrade automático de qualidade"
            hint="Substituir arquivo quando uma versão de melhor qualidade é baixada"
            checked={boolVal('auto_upgrade_quality')}
            onChange={(v) => set('auto_upgrade_quality', v)}
          />
        </div>
      </section>

      {/* Metadados de Áudio */}
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Metadados de Áudio</h2>
        <div className="atum-settings-group">
          <Toggle
            label="Escrever metadados nos arquivos"
            hint="Ao editar metadados na biblioteca, salvar também nas tags do arquivo (ID3, Vorbis, etc.)"
            checked={boolVal('write_audio_metadata')}
            onChange={(v) => set('write_audio_metadata', v)}
          />
          <Toggle
            label="Embutir artwork nos arquivos"
            hint="Salvar a capa encontrada como tag de imagem nos arquivos de áudio"
            checked={boolVal('embed_cover_in_audio')}
            onChange={(v) => set('embed_cover_in_audio', v)}
          />
        </div>
      </section>

      {/* Integrações */}
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
                  onClick={() => testConnection('tmdb', { api_key: val('tmdb_api_key') })}
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
                  onClick={() => testConnection('plex', { url: val('plex_url'), token: val('plex_token') })}
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
                  onClick={() => testConnection('jellyfin', { url: val('jellyfin_url'), api_key: val('jellyfin_api_key') })}
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

      {/* Enriquecimento / AI */}
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Enriquecimento de Dados</h2>
        <div className="atum-settings-group">
          {enrichmentStats && (
            <div className="atum-settings-enrichment-stats">
              <span className="atum-settings-enrichment-stat">
                <strong>{enrichmentStats.enriched}</strong> enriquecidos
              </span>
              <span className="atum-settings-enrichment-stat atum-settings-enrichment-stat--pending">
                <strong>{enrichmentStats.pending}</strong> pendentes
              </span>
              {enrichmentStats.errors > 0 && (
                <span className="atum-settings-enrichment-stat atum-settings-enrichment-stat--error">
                  <strong>{enrichmentStats.errors}</strong> com erro
                </span>
              )}
              <span className="atum-settings-enrichment-stat" style={{ opacity: 0.6 }}>
                {enrichmentStats.total} total
              </span>
            </div>
          )}
          <Toggle
            label="Enriquecimento com LLM habilitado"
            hint="Usar IA para inferir moods, contextos e refinar sub-gêneros (requer Ollama ou OpenRouter)"
            checked={boolVal('enrichment_enabled')}
            onChange={(v) => set('enrichment_enabled', v)}
          />
          <Field
            label="Intervalo entre ciclos (segundos)"
            hint="Tempo de espera entre cada ciclo do daemon de enriquecimento"
          >
            <input
              type="number"
              className="atum-settings-input"
              min={30}
              max={86400}
              value={val('enrichment_interval')}
              onChange={(e) => set('enrichment_interval', Math.max(30, Math.min(86400, Number(e.target.value) || 300)))}
              placeholder="300"
            />
          </Field>
          <Field
            label="Itens por ciclo (batch size)"
            hint="Quantos itens processar a cada ciclo do daemon"
          >
            <input
              type="number"
              className="atum-settings-input"
              min={1}
              max={100}
              value={val('enrichment_batch_size')}
              onChange={(e) => set('enrichment_batch_size', Math.max(1, Math.min(100, Number(e.target.value) || 10)))}
              placeholder="10"
            />
          </Field>
          <Field
            label="Retry automático (horas)"
            hint="Re-tentar itens com erro após X horas (0 = desativado, requer 'enrichment reset' manual)"
          >
            <input
              type="number"
              className="atum-settings-input"
              min={0}
              max={720}
              value={val('enrichment_retry_after_hours')}
              onChange={(e) => set('enrichment_retry_after_hours', Math.max(0, Math.min(720, Number(e.target.value) || 0)))}
              placeholder="24"
            />
          </Field>

          <div className="atum-settings-integration">
            <div className="atum-settings-integration-header">
              <span className="atum-settings-integration-name">AI Provider</span>
              {testResults.ollama && (
                <span className={`atum-settings-integration-status atum-settings-integration-status--${testResults.ollama.ok ? 'ok' : 'error'}`}>
                  {testResults.ollama.ok ? 'Conectado' : 'Erro'}
                </span>
              )}
              {testResults.openrouter && (
                <span className={`atum-settings-integration-status atum-settings-integration-status--${testResults.openrouter.ok ? 'ok' : 'error'}`}>
                  {testResults.openrouter.ok ? 'Conectado' : 'Erro'}
                </span>
              )}
            </div>
            <div className="atum-settings-group">
              <Field label="Provider primário" hint="Ollama (local, gratuito) ou OpenRouter (cloud)">
                <select
                  className="atum-settings-select"
                  value={val('ai_provider') || 'ollama'}
                  onChange={(e) => set('ai_provider', e.target.value)}
                >
                  <option value="ollama">Ollama (local)</option>
                  <option value="openrouter">OpenRouter (cloud)</option>
                </select>
              </Field>
              <Field
                label="Modelo"
                hint="Ex: llama3.1:8b (Ollama) ou meta-llama/llama-3.1-8b-instruct (OpenRouter)"
                value={val('ai_model')}
                onChange={(v) => set('ai_model', v)}
                placeholder="llama3.1:8b"
              />
              {val('ai_provider') === 'ollama' ? (
                <>
                  <Field
                    label="URL do Ollama"
                    hint="Endereço do servidor Ollama"
                    value={val('ai_base_url')}
                    onChange={(v) => set('ai_base_url', v)}
                    placeholder="http://ollama:11434"
                  />
                  <div className="atum-settings-field-row">
                    <button
                      type="button"
                      className="atum-btn"
                      disabled={testing.ollama}
                      onClick={() => testConnection('ollama', { url: val('ai_base_url') || 'http://ollama:11434' })}
                    >
                      {testing.ollama ? 'Testando...' : 'Testar Conexão'}
                    </button>
                  </div>
                  {testResults.ollama && (
                    <div className={`atum-settings-test-result atum-settings-test-result--${testResults.ollama.ok ? 'ok' : 'error'}`}>
                      {testResults.ollama.ok ? testResults.ollama.message : testResults.ollama.error}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <Field
                    label="API Key"
                    hint="Sua chave de API do OpenRouter"
                    type="password"
                    value={val('ai_api_key')}
                    onChange={(v) => set('ai_api_key', v)}
                    placeholder="sk-or-..."
                  />
                  <div className="atum-settings-field-row">
                    <button
                      type="button"
                      className="atum-btn"
                      disabled={testing.openrouter}
                      onClick={() => testConnection('openrouter', { api_key: val('ai_api_key') })}
                    >
                      {testing.openrouter ? 'Testando...' : 'Testar Conexão'}
                    </button>
                  </div>
                  {testResults.openrouter && (
                    <div className={`atum-settings-test-result atum-settings-test-result--${testResults.openrouter.ok ? 'ok' : 'error'}`}>
                      {testResults.openrouter.ok ? testResults.openrouter.message : testResults.openrouter.error}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="atum-settings-integration">
            <div className="atum-settings-integration-header">
              <span className="atum-settings-integration-name">Fallback (opcional)</span>
            </div>
            <div className="atum-settings-group">
              <Field label="Provider fallback" hint="Se o primário falhar, tentar este">
                <select
                  className="atum-settings-select"
                  value={val('ai_fallback_provider') || ''}
                  onChange={(e) => set('ai_fallback_provider', e.target.value)}
                >
                  <option value="">Nenhum</option>
                  <option value="ollama">Ollama</option>
                  <option value="openrouter">OpenRouter</option>
                </select>
              </Field>
              {val('ai_fallback_provider') && (
                <>
                  <Field
                    label="Modelo fallback"
                    value={val('ai_fallback_model')}
                    onChange={(v) => set('ai_fallback_model', v)}
                    placeholder="meta-llama/llama-3.1-8b-instruct"
                  />
                  {val('ai_fallback_provider') === 'ollama' && (
                    <Field
                      label="URL do Ollama (fallback)"
                      hint="Endereço do servidor Ollama de fallback"
                      value={val('ai_fallback_base_url')}
                      onChange={(v) => set('ai_fallback_base_url', v)}
                      placeholder="http://ollama:11434"
                    />
                  )}
                  {val('ai_fallback_provider') === 'openrouter' && (
                    <Field
                      label="API Key fallback"
                      type="password"
                      value={val('ai_fallback_api_key')}
                      onChange={(v) => set('ai_fallback_api_key', v)}
                      placeholder="sk-or-..."
                    />
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Biblioteca */}
      <section className="atum-settings-section">
        <h2 className="atum-settings-section-title">Biblioteca</h2>
        <div className="atum-settings-group">
          <div className="atum-settings-field">
            <span className="atum-settings-label">Reorganizar Biblioteca</span>
            <span className="atum-settings-hint">
              Aplica o padrão Plex-compatible aos arquivos existentes. Use "Preview" para ver o que seria feito.
            </span>
            <div className="atum-settings-field-row" style={{ marginTop: '0.5rem' }}>
              <button
                type="button"
                className="atum-btn"
                disabled={reorganizing}
                onClick={() => reorganizeLibrary(true)}
              >
                {reorganizing ? 'Processando...' : 'Preview (dry-run)'}
              </button>
              <button
                type="button"
                className="atum-btn atum-btn-primary"
                disabled={reorganizing}
                onClick={() => {
                  if (confirm('Reorganizar a biblioteca? Arquivos serão renomeados/movidos conforme as configurações de organização.')) {
                    reorganizeLibrary(false);
                  }
                }}
              >
                Reorganizar
              </button>
            </div>
            {reorganizeResult && (
              <div style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
                <p style={{ marginBottom: '0.25rem' }}>
                  {reorganizeResult.dry_run ? 'Preview: ' : ''}
                  <strong>{reorganizeResult.processed}</strong> processados,{' '}
                  <strong>{reorganizeResult.skipped}</strong> pulados,{' '}
                  <strong>{reorganizeResult.errors}</strong> erros
                </p>
                {reorganizeResult.details.length > 0 && (
                  <details style={{ marginTop: '0.5rem' }}>
                    <summary style={{ cursor: 'pointer', color: 'var(--atum-muted)' }}>
                      Detalhes ({reorganizeResult.details.length})
                    </summary>
                    <pre style={{
                      marginTop: '0.25rem',
                      padding: '0.5rem',
                      background: 'var(--atum-bg)',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      maxHeight: '200px',
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                    }}>
                      {reorganizeResult.details.join('\n')}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Ações */}
      <div className="atum-settings-actions">
        {saved && <span className="atum-settings-saved">Salvo com sucesso</span>}
        <button
          type="button"
          className="atum-btn"
          disabled={!hasDirty}
          onClick={() => { setDirty({}); fetchSettings(); }}
        >
          Descartar
        </button>
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          disabled={!hasDirty || saving}
          onClick={save}
        >
          {saving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>
    </div>
  );
}
