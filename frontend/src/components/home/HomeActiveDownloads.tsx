import { Link } from 'react-router-dom';
import { IoChevronForward } from 'react-icons/io5';
import { CoverImage } from '../CoverImage';
import { normalizeProgress, toContentType } from '../../hooks/useHome';
import type { ActiveDownload } from '../../types/library';

interface HomeActiveDownloadsProps {
  downloads: ActiveDownload[];
}

export function HomeActiveDownloads({ downloads }: HomeActiveDownloadsProps) {
  if (downloads.length === 0) return null;

  return (
    <section className="home-rail home-downloads-active" aria-label="Downloads ativos">
      <div className="home-rail-header">
        <h2 className="home-rail-title">Downloads Ativos</h2>
        <Link to="/downloads" className="home-rail-link">
          Ver todos <IoChevronForward size={14} />
        </Link>
      </div>
      <div className="home-active-dl-list">
        {downloads.slice(0, 4).map((dl) => {
          const pct = normalizeProgress(dl.progress);
          return (
            <Link key={dl.id} to="/downloads" className="home-active-dl-card">
              <div className="home-active-dl-cover">
                <CoverImage
                  contentType={toContentType(dl.content_type)}
                  title={dl.name || ''}
                  size="card"
                  downloadId={dl.id}
                />
              </div>
              <div className="home-active-dl-info">
                <span className="home-active-dl-name">{dl.name || '—'}</span>
                <div className="home-active-dl-bar">
                  <div className="home-active-dl-bar-fill" style={{ width: `${pct}%` }}>
                    <span className="home-active-dl-bar-text">{pct.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
