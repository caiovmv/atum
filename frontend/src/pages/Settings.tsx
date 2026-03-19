import { useSettings } from '../hooks/useSettings';
import { Skeleton } from '../components/Skeleton';
import { AIPromptsSection } from '../components/settings/AIPromptsSection';
import { GeneralSection } from '../components/settings/GeneralSection';
import { IntegrationsSection } from '../components/settings/IntegrationsSection';
import { EnrichmentSection } from '../components/settings/EnrichmentSection';
import { LibrarySection } from '../components/settings/LibrarySection';
import { PlayStatsSection } from '../components/settings/PlayStatsSection';
import { CertificatesSection } from '../components/settings/CertificatesSection';
import './Settings.css';

export function Settings() {
  const s = useSettings();

  if (s.loading) {
    return (
      <div className="atum-page settings-page atum-settings" aria-busy="true">
        <h1 className="atum-settings-title">Configurações</h1>
        <div className="atum-settings-skeleton">
          <Skeleton width="60%" height="0.9rem" borderRadius="4px" />
          <section className="atum-settings-section">
            <Skeleton width="8rem" height="1.1rem" borderRadius="4px" />
            <div className="atum-settings-skeleton-fields">
              <Skeleton width="100%" height="2.5rem" borderRadius="6px" />
              <Skeleton width="100%" height="2.5rem" borderRadius="6px" />
            </div>
          </section>
          <section className="atum-settings-section">
            <Skeleton width="10rem" height="1.1rem" borderRadius="4px" />
            <div className="atum-settings-skeleton-fields">
              <Skeleton width="100%" height="2.5rem" borderRadius="6px" />
            </div>
          </section>
        </div>
      </div>
    );
  }

  if (s.fetchError) {
    return (
      <div className="atum-page settings-page atum-settings">
        <h1 className="atum-settings-title">Configurações</h1>
        <div className="atum-settings-test-result atum-settings-test-result--error atum-settings-mb-1">
          {s.fetchError}
        </div>
        <button type="button" className="atum-btn" onClick={() => s.refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="atum-page settings-page atum-settings">
      <h1 className="atum-settings-title">Configurações</h1>
      <p className="atum-settings-desc">Gerencie configurações do sistema, organização e integrações.</p>

      <GeneralSection val={s.val} set={s.set} boolVal={s.boolVal} />

      <IntegrationsSection
        val={s.val}
        set={s.set}
        boolVal={s.boolVal}
        testResults={s.testResults}
        testing={s.testing}
        onTestConnection={s.handleTestConnection}
      />

      <EnrichmentSection
        val={s.val}
        set={s.set}
        boolVal={s.boolVal}
        enrichmentStats={s.enrichmentStats}
        testResults={s.testResults}
        testing={s.testing}
        onTestConnection={s.handleTestConnection}
      />

      <AIPromptsSection />

      <LibrarySection
        reorganizing={s.reorganizing}
        reorganizeResult={s.reorganizeResult}
        onReorganize={s.handleReorganize}
      />

      <PlayStatsSection />

      <CertificatesSection />

      <div className="atum-settings-actions">
        {s.saved && <span className="atum-settings-saved">Salvo com sucesso</span>}
        <button
          type="button"
          className="atum-btn"
          disabled={!s.hasDirty}
          onClick={s.discard}
        >
          Descartar
        </button>
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          disabled={!s.hasDirty || s.saving}
          onClick={s.save}
        >
          {s.saving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>
    </div>
  );
}
