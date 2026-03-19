import { resetPlayCount } from '../../api/playlists';

export function PlayStatsSection() {
  return (
    <section className="atum-settings-section">
      <h2 className="atum-settings-section-title">Estatísticas de Reprodução</h2>
      <p className="atum-settings-hint" style={{ marginBottom: '0.75rem' }}>
        A playlist "Mais Tocadas" é gerada automaticamente a partir dos contadores de reprodução.
      </p>
      <button
        type="button"
        className="atum-btn"
        style={{ color: 'var(--atum-error)' }}
        onClick={async () => {
          if (!window.confirm('Zerar todos os contadores de reprodução? Esta ação não pode ser desfeita.')) return;
          try {
            const data = await resetPlayCount();
            alert(`Contadores zerados (${data.reset ?? 0} registros removidos).`);
          } catch {
            if (import.meta.env.DEV) console.warn('[Settings] resetPlayCount failed');
          }
        }}
      >
        Zerar contadores de reprodução
      </button>
    </section>
  );
}
