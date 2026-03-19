import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { getAIPrompts, updateAIPrompt, dryRunAIPrompt } from '../../api/ai';
import { Skeleton } from '../Skeleton';
import { Input, Textarea } from '../Input';

interface DryRunResult {
  messages: Array<{ role: string; content: string }>;
  response: { content: string; model: string; provider: string };
}

export function AIPromptsSection() {
  const { data: promptsData, loading, refetch } = useFetch((signal) => getAIPrompts({ signal }), []);
  const prompts = promptsData ?? [];
  const [edits, setEdits] = useState<Record<string, { system?: string; temperature?: number }>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [dryRun, setDryRun] = useState<Record<string, { loading: boolean; result?: DryRunResult; error?: string; jsonValid?: boolean }>>({});
  const [dryRunContext, setDryRunContext] = useState<Record<string, Record<string, string | number>>>({});

  const setContextField = (promptId: string, field: string, value: string | number) => {
    setDryRunContext((prev) => ({
      ...prev,
      [promptId]: { ...(prev[promptId] || {}), [field]: value },
    }));
  };

  const savePrompt = async (id: string) => {
    const e = edits[id];
    if (!e) return;
    setSaving((prev) => ({ ...prev, [id]: true }));
    try {
      await updateAIPrompt(id, { system: e.system, temperature: e.temperature });
      refetch();
      setEdits((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } finally {
      setSaving((prev) => ({ ...prev, [id]: false }));
    }
  };

  const runDryRun = async (id: string) => {
    setDryRun((prev) => ({ ...prev, [id]: { loading: true } }));
    try {
      const ctx = dryRunContext[id] || {};
      const data = await dryRunAIPrompt(id, { user_input: (ctx.user_input as string) || '', context: ctx });
      let jsonValid: boolean | undefined;
      if (data.response?.content && (prompts.find((x) => x.id === id)?.response_type === 'json')) {
        try {
          const text = data.response.content;
          const start = text.indexOf('{');
          const end = text.lastIndexOf('}') + 1;
          if (start >= 0 && end > start) {
            JSON.parse(text.slice(start, end));
            jsonValid = true;
          } else {
            jsonValid = false;
          }
        } catch {
          jsonValid = false;
        }
      }
      setDryRun((prev) => ({ ...prev, [id]: { loading: false, result: data as DryRunResult, jsonValid } }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setDryRun((prev) => ({ ...prev, [id]: { loading: false, error: msg } }));
    }
  };

  if (loading) {
    return (
      <section className="atum-settings-section" aria-busy="true">
        <h2 className="atum-settings-section-title">System Prompts</h2>
        <div className="atum-settings-prompts-skeleton">
          {Array.from({ length: 2 }, (_, i) => (
            <div key={i} className="atum-settings-prompt-card">
              <Skeleton width="8rem" height="1rem" borderRadius="4px" />
              <Skeleton width="100%" height="5rem" borderRadius="6px" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="atum-settings-section">
      <h2 className="atum-settings-section-title">System Prompts</h2>
      <p className="atum-settings-hint" style={{ marginBottom: '1rem' }}>
        Edite os prompts por funcionalidade. Salve antes de testar. Use Dry-run para ver todas as mensagens trocadas.
      </p>
      <div className="atum-settings-prompts-grid">
        {prompts.map((p) => {
          const sysVal = edits[p.id]?.system ?? p.system;
          const tempVal = edits[p.id]?.temperature ?? p.temperature;
          const dr = dryRun[p.id];
          const ctxVal = dryRunContext[p.id] || {};
          const hasEdits = edits[p.id] && (edits[p.id]?.system !== undefined || edits[p.id]?.temperature !== undefined);
          const schema = p.context_schema || [];
          return (
            <div key={p.id} className="atum-settings-prompt-card">
              <h3 className="atum-settings-prompt-title">{p.label}</h3>
              <p className="atum-settings-hint">{p.description}</p>
              <div className="atum-settings-field">
                <span className="atum-settings-label">System prompt</span>
                <Textarea
                  className="atum-settings-prompt-textarea"
                  rows={6}
                  value={sysVal}
                  onChange={(e) => setEdits((prev) => ({ ...prev, [p.id]: { ...prev[p.id], system: e.target.value } }))}
                  placeholder="Prompt do sistema..."
                />
              </div>
              <div className="atum-settings-field">
                <span className="atum-settings-label">Temperatura</span>
                <Input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={tempVal}
                  onChange={(e) => setEdits((prev) => ({ ...prev, [p.id]: { ...prev[p.id], temperature: Number(e.target.value) || 0.4 } }))}
                />
              </div>
              {schema.length > 0 && (
                <div className="atum-settings-field">
                  <span className="atum-settings-label">Contexto para dry-run</span>
                  {schema.map((f) => (
                    <div key={f.name} className="atum-settings-field" style={{ marginTop: '0.4rem' }}>
                      <span className="atum-settings-label" style={{ fontSize: '0.8rem' }}>
                        {f.label}
                        {f.required && <span style={{ color: 'var(--atum-accent)' }}> *</span>}
                      </span>
                      {(f.type === 'string' && (f.name === 'library_lines' || f.name === 'existing')) || f.type === 'json' ? (
                        <Textarea
                          rows={3}
                          placeholder={f.placeholder}
                          value={String(ctxVal[f.name] ?? '')}
                          onChange={(e) => setContextField(p.id, f.name, e.target.value)}
                        />
                      ) : (
                        <Input
                          type={f.type === 'number' ? 'number' : 'text'}
                          placeholder={f.placeholder}
                          value={String(ctxVal[f.name] ?? '')}
                          onChange={(e) => setContextField(p.id, f.name, f.type === 'number' ? (Number(e.target.value) || 0) : e.target.value)}
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
              {p.expected_json_schema && (
                <details className="atum-settings-prompt-dry-result" style={{ marginTop: '0.5rem' }}>
                  <summary className="atum-settings-hint" style={{ cursor: 'pointer' }}>Schema JSON esperado</summary>
                  <pre className="atum-settings-reorg-pre" style={{ marginTop: '0.25rem', fontSize: '0.75rem' }}>{p.expected_json_schema}</pre>
                </details>
              )}
              <div className="atum-settings-field-row" style={{ gap: '0.5rem', flexWrap: 'wrap' }}>
                {hasEdits && (
                  <button type="button" className="atum-btn atum-btn-primary" disabled={saving[p.id]} onClick={() => savePrompt(p.id)}>
                    {saving[p.id] ? 'Salvando...' : 'Salvar'}
                  </button>
                )}
                <button type="button" className="atum-btn" disabled={dr?.loading} onClick={() => runDryRun(p.id)}>
                  {dr?.loading ? 'Testando...' : 'Testar (Dry-run)'}
                </button>
              </div>
              {dr?.result && (
                <details className="atum-settings-prompt-dry-result" open>
                  <summary>Mensagens trocadas</summary>
                  <div className="atum-settings-prompt-messages">
                    {dr.result.messages.map((m, i) => (
                      <div key={i} className={`atum-settings-prompt-msg atum-settings-prompt-msg--${m.role}`}>
                        <strong>{m.role}:</strong>
                        <pre>{m.content}</pre>
                      </div>
                    ))}
                  </div>
                  <p className="atum-settings-hint">Modelo: {dr.result.response.model} ({dr.result.response.provider})</p>
                  {dr.jsonValid !== undefined && (
                    <p className={`atum-settings-hint ${dr.jsonValid ? 'atum-settings-test-result--ok' : 'atum-settings-test-result--error'}`}>
                      JSON: {dr.jsonValid ? 'válido' : 'inválido ou não parseável'}
                    </p>
                  )}
                </details>
              )}
              {dr?.error && <p className="atum-settings-test-result atum-settings-test-result--error">{dr.error}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
