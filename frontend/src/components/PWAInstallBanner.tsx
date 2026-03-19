import { IoDownloadOutline, IoClose } from 'react-icons/io5';
import { usePWAInstall } from '../hooks/usePWAInstall';
import './PWAInstallBanner.css';

export function PWAInstallBanner() {
  const { showBanner, install, dismiss } = usePWAInstall();

  if (!showBanner) return null;

  return (
    <div className="pwa-install-banner" role="region" aria-label="Instalar aplicativo">
      <div className="pwa-install-banner-inner">
        <div className="pwa-install-banner-content">
          <IoDownloadOutline className="pwa-install-banner-icon" aria-hidden />
          <div>
            <p className="pwa-install-banner-title">Instalar Atum</p>
            <p className="pwa-install-banner-desc">Use como app no seu dispositivo</p>
          </div>
        </div>
        <div className="pwa-install-banner-actions">
          <button
            type="button"
            className="atum-btn atum-btn-primary pwa-install-banner-btn"
            onClick={install}
            aria-label="Instalar aplicativo Atum"
          >
            Instalar
          </button>
          <button
            type="button"
            className="pwa-install-banner-dismiss"
            onClick={dismiss}
            aria-label="Não mostrar novamente"
          >
            <IoClose size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
