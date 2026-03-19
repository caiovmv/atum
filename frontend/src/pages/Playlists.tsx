import { useNavigate } from 'react-router-dom';
import { IoAdd, IoList, IoMusicalNotes, IoPlay, IoRadio, IoSparkles } from 'react-icons/io5';
import { EmptyState } from '../components/EmptyState';
import { MediaCard } from '../components/MediaCard';
import { SkeletonCard } from '../components/Skeleton';
import { PlaylistCreateForm } from '../components/playlists/PlaylistCreateForm';
import { getCollectionIcon, getCollectionKindLabel } from '../components/playlists/playlistUtils';
import { usePlaylists, type TabKind } from '../hooks/usePlaylists';
import type { Playlist } from '../api/playlists';
import './Playlists.css';

const TABS: { value: TabKind; label: string; icon: React.ReactNode }[] = [
  { value: 'all', label: 'Todos', icon: <IoList size={14} /> },
  { value: 'static', label: 'Playlists', icon: <IoMusicalNotes size={14} /> },
  { value: 'dynamic_rules', label: 'Sintonias', icon: <IoRadio size={14} /> },
  { value: 'dynamic_ai', label: 'AI Mix', icon: <IoSparkles size={14} /> },
];

export function Playlists() {
  const pl = usePlaylists();
  const navigate = useNavigate();

  if (pl.loading) {
    return (
      <div className="atum-page playlists-page">
        <h1 className="playlists-title">Coleções</h1>
        <div className="playlists-skeleton-grid" aria-busy="true">
          {Array.from({ length: 8 }, (_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="atum-page playlists-page">
      <div className="playlists-header">
        <h1 className="playlists-title">Coleções</h1>
        <button type="button" className="playlists-create-btn" onClick={() => pl.setCreating(true)}>
          <IoAdd size={18} /> Nova Coleção
        </button>
      </div>

      {pl.fetchError && (
        <div className="playlists-error" role="alert">
          <span>{pl.fetchError}</span>{' '}
          <button type="button" className="atum-btn atum-btn-small" onClick={() => pl.refetch()}>
            Tentar novamente
          </button>
        </div>
      )}

      <div className="playlists-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            className={`playlists-tab${pl.activeTab === tab.value ? ' playlists-tab--active' : ''}`}
            onClick={() => pl.handleTabChange(tab.value)}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {pl.creating && (
        <PlaylistCreateForm
          createMode={pl.createMode}
          setCreateMode={pl.setCreateMode}
          newName={pl.newName}
          setNewName={pl.setNewName}
          newDescription={pl.newDescription}
          setNewDescription={pl.setNewDescription}
          newRules={pl.newRules}
          setNewRules={pl.setNewRules}
          newPrompt={pl.newPrompt}
          setNewPrompt={pl.setNewPrompt}
          onCreate={pl.handleCreate}
          onCancel={pl.resetCreateForm}
          addRule={pl.addRule}
        />
      )}

      {pl.playlists.length === 0 ? (
        <EmptyState title="Nenhuma coleção ainda." />
      ) : (
        <div className="playlists-grid">
          {pl.playlists.map((p: Playlist) => (
            <MediaCard
              key={p.id}
              cover={{
                src: `/api/playlists/${p.id}/cover`,
                alt: p.name,
              }}
              coverPlaceholder={getCollectionIcon(p.kind, p.system_kind)}
              coverShape="square"
              badge={getCollectionIcon(p.kind, p.system_kind)}
              title={p.name}
              meta={[
                getCollectionKindLabel(p.kind, p.system_kind),
                `${p.track_count} ${p.track_count === 1 ? 'faixa' : 'faixas'}`,
              ].filter(Boolean)}
              showSeLe={false}
              primaryAction={
                <button
                  type="button"
                  className="media-card-play-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/playlists/${p.id}`);
                  }}
                  aria-label={`Abrir ${p.name}`}
                >
                  <IoPlay size={24} />
                </button>
              }
              actions={<></>}
              onClick={() => navigate(`/playlists/${p.id}`)}
              clickAriaLabel={`Abrir coleção ${p.name}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
