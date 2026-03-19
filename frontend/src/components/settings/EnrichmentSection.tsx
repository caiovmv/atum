import { Toggle, Field } from './SettingsForm';
import { Input, Select } from '../Input';
import type { EnrichmentStats } from '../../api/settings';

interface TestResult {
  ok: boolean;
  message?: string;
  error?: string;
}

interface EnrichmentSectionProps {
  val: (key: string) => string;
  set: (key: string, value: unknown) => void;
  boolVal: (key: string) => boolean;
  enrichmentStats: EnrichmentStats | null;
  testResults: Record<string, TestResult>;
  testing: Record<string, boolean>;
  onTestConnection: (service: string, params: Record<string, string>) => void;
}

export function EnrichmentSection({
  val,
  set,
  boolVal,
  enrichmentStats,
  testResults,
  testing,
  onTestConnection,
}: EnrichmentSectionProps) {
  return (
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
            <span className="atum-settings-enrichment-stat atum-settings-stat-muted">
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
          <Input
            type="number"
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
          <Input
            type="number"
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
          <Input
            type="number"
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
              <Select
                value={val('ai_provider') || 'ollama'}
                onChange={(e) => set('ai_provider', e.target.value)}
              >
                <option value="ollama">Ollama (local)</option>
                <option value="openrouter">OpenRouter (cloud)</option>
              </Select>
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
                    onClick={() => onTestConnection('ollama', { url: val('ai_base_url') || 'http://ollama:11434' })}
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
                    onClick={() => onTestConnection('openrouter', { api_key: val('ai_api_key') })}
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
              <Select
                value={val('ai_fallback_provider') || ''}
                onChange={(e) => set('ai_fallback_provider', e.target.value)}
              >
                <option value="">Nenhum</option>
                <option value="ollama">Ollama</option>
                <option value="openrouter">OpenRouter</option>
              </Select>
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

        <div className="atum-settings-integration">
          <div className="atum-settings-integration-header">
            <span className="atum-settings-integration-name">Parâmetros do Modelo</span>
          </div>
          <span className="atum-settings-hint" style={{ display: 'block', marginBottom: '0.5rem' }}>
            Configurações globais: janela de contexto e max tokens. Valores máximos por padrão.
          </span>
          <div className="atum-settings-group">
            <Field
              label="Janela de contexto (tokens)"
              hint="Ollama: até 128K. OpenRouter depende do modelo."
            >
              <Input
                type="number"
                min={2048}
                max={131072}
                step={4096}
                value={val('ai_num_ctx') || '131072'}
                onChange={(e) => set('ai_num_ctx', Math.max(2048, Math.min(131072, Number(e.target.value) || 131072)))}
                placeholder="131072"
              />
            </Field>
            <Field
              label="Max tokens de saída"
              hint="Máximo de tokens gerados na resposta"
            >
              <Input
                type="number"
                min={256}
                max={32768}
                step={512}
                value={val('ai_num_predict') || val('ai_max_tokens') || '8192'}
                onChange={(e) => {
                  const v = Math.max(256, Math.min(32768, Number(e.target.value) || 8192));
                  set('ai_num_predict', v);
                  set('ai_max_tokens', v);
                }}
                placeholder="8192"
              />
            </Field>
            <Field
              label="Temperatura padrão"
              hint="0 = determinístico, 2 = mais criativo"
            >
              <Input
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={val('ai_temperature') || '0.4'}
                onChange={(e) => set('ai_temperature', Math.max(0, Math.min(2, Number(e.target.value) || 0.4)))}
                placeholder="0.4"
              />
            </Field>
          </div>
        </div>
      </div>
    </section>
  );
}
