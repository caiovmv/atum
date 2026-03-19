import { useState, useEffect } from 'react';
import { IoRefresh } from 'react-icons/io5';
import { getUpdateSW, PWA_NEED_REFRESH_EVENT } from '../utils/pwaUpdate';
import './PWAUpdatePrompt.css';

export function PWAUpdatePrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const handler = () => setShow(true);
    window.addEventListener(PWA_NEED_REFRESH_EVENT, handler);
    return () => window.removeEventListener(PWA_NEED_REFRESH_EVENT, handler);
  }, []);

  const handleReload = () => {
    const updateSW = getUpdateSW();
    if (updateSW) updateSW();
  };

  const handleLater = () => {
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="pwa-update-prompt" role="alert" aria-live="polite">
      <div className="pwa-update-prompt-inner">
        <div className="pwa-update-prompt-content">
          <IoRefresh className="pwa-update-prompt-icon" aria-hidden />
          <div>
            <p className="pwa-update-prompt-title">Nova versão disponível</p>
            <p className="pwa-update-prompt-desc">Recarregue para atualizar o aplicativo</p>
          </div>
        </div>
        <div className="pwa-update-prompt-actions">
          <button
            type="button"
            className="atum-btn pwa-update-prompt-later"
            onClick={handleLater}
            aria-label="Atualizar depois"
          >
            Depois
          </button>
          <button
            type="button"
            className="atum-btn atum-btn-primary pwa-update-prompt-reload"
            onClick={handleReload}
            aria-label="Recarregar para atualizar"
          >
            Recarregar
          </button>
        </div>
      </div>
    </div>
  );
}
