export function CertificatesSection() {
  return (
    <section className="atum-settings-section">
      <h2 className="atum-settings-section-title">Certificados HTTPS</h2>
      <p className="atum-settings-hint" style={{ marginBottom: '0.75rem' }}>
        Para acessar o Atum sem avisos de segurança, instale o certificado raiz nos seus dispositivos.
      </p>
      <button
        type="button"
        className="atum-btn atum-btn-primary"
        onClick={() => {
          const a = document.createElement('a');
          a.href = '/api/settings/certificates';
          a.download = 'atum-certificados.zip';
          a.click();
        }}
      >
        Baixar certificados (.zip)
      </button>
      <div style={{ marginTop: '1rem' }}>
        <details className="atum-settings-reorg-details">
          <summary className="atum-settings-reorg-details-summary">Windows</summary>
          <pre className="atum-settings-reorg-pre" style={{ whiteSpace: 'pre-wrap' }}>
            {`Abra o Prompt como Administrador:\ncertutil -addstore "Root" atum-ca.crt\n\nOu: clique duas vezes no arquivo > Instalar Certificado > Máquina Local > "Autoridades de Certificação Raiz Confiáveis".`}
          </pre>
        </details>
        <details className="atum-settings-reorg-details">
          <summary className="atum-settings-reorg-details-summary">macOS</summary>
          <pre className="atum-settings-reorg-pre" style={{ whiteSpace: 'pre-wrap' }}>
            {`sudo security add-trusted-cert -d -r trustRoot \\\n  -k /Library/Keychains/System.keychain atum-ca.crt`}
          </pre>
        </details>
        <details className="atum-settings-reorg-details">
          <summary className="atum-settings-reorg-details-summary">Linux</summary>
          <pre className="atum-settings-reorg-pre" style={{ whiteSpace: 'pre-wrap' }}>
            {`sudo cp atum-ca.crt /usr/local/share/ca-certificates/\nsudo update-ca-certificates`}
          </pre>
        </details>
        <details className="atum-settings-reorg-details">
          <summary className="atum-settings-reorg-details-summary">iOS</summary>
          <pre className="atum-settings-reorg-pre" style={{ whiteSpace: 'pre-wrap' }}>
            {`1. Abra o .crt no Safari (AirDrop ou link direto).\n2. Ajustes > Geral > VPN e Gerenciamento de Dispositivo > "Atum Root CA" > Instalar.\n3. Ajustes > Geral > Sobre > Certificados Confiáveis > ativar "Atum Root CA".`}
          </pre>
        </details>
        <details className="atum-settings-reorg-details">
          <summary className="atum-settings-reorg-details-summary">Android</summary>
          <pre className="atum-settings-reorg-pre" style={{ whiteSpace: 'pre-wrap' }}>
            {`1. Configurações > Segurança > Criptografia e Credenciais > Instalar certificado > CA.\n2. Selecione o arquivo atum-ca.crt.`}
          </pre>
        </details>
      </div>
    </section>
  );
}
