interface ReorganizeResult {
  processed: number;
  skipped: number;
  errors: number;
  dry_run: boolean;
  details: string[];
}

interface LibrarySectionProps {
  reorganizing: boolean;
  reorganizeResult: ReorganizeResult | null;
  onReorganize: (dryRun: boolean) => void;
}

export function LibrarySection({ reorganizing, reorganizeResult, onReorganize }: LibrarySectionProps) {
  return (
    <section className="atum-settings-section">
      <h2 className="atum-settings-section-title">Biblioteca</h2>
      <div className="atum-settings-group">
        <div className="atum-settings-field">
          <span className="atum-settings-label">Reorganizar Biblioteca</span>
          <span className="atum-settings-hint">
            Aplica o padrão Plex-compatible aos arquivos existentes. Use "Preview" para ver o que seria feito.
          </span>
          <div className="atum-settings-field-row atum-settings-mt-half">
            <button
              type="button"
              className="atum-btn"
              disabled={reorganizing}
              onClick={() => onReorganize(true)}
            >
              {reorganizing ? 'Processando...' : 'Preview (dry-run)'}
            </button>
            <button
              type="button"
              className="atum-btn atum-btn-primary"
              disabled={reorganizing}
              onClick={() => {
                if (confirm('Reorganizar a biblioteca? Arquivos serão renomeados/movidos conforme as configurações de organização.')) {
                  onReorganize(false);
                }
              }}
            >
              Reorganizar
            </button>
          </div>
          {reorganizeResult && (
            <div className="atum-settings-reorg-result">
              <p className="atum-settings-reorg-summary">
                {reorganizeResult.dry_run ? 'Preview: ' : ''}
                <strong>{reorganizeResult.processed}</strong> processados,{' '}
                <strong>{reorganizeResult.skipped}</strong> pulados,{' '}
                <strong>{reorganizeResult.errors}</strong> erros
              </p>
              {reorganizeResult.details.length > 0 && (
                <details className="atum-settings-reorg-details">
                  <summary className="atum-settings-reorg-details-summary">
                    Detalhes ({reorganizeResult.details.length})
                  </summary>
                  <pre className="atum-settings-reorg-pre">
                    {reorganizeResult.details.join('\n')}
                  </pre>
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
