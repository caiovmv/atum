import { useFeeds } from '../hooks/useFeeds';
import {
  FeedsAddForm,
  FeedsAISection,
  FeedsList,
  FeedsPendingSection,
} from '../components/feeds';
import './Feeds.css';

export function Feeds() {
  const f = useFeeds();

  return (
    <div className="atum-page feeds-page atum-feeds">
      <h1 className="atum-feeds-title">Feeds</h1>
      <p className="atum-feeds-desc">
        Inscreva feeds RSS (música, filmes, séries). Verifique para ver novidades e adicione aos pendentes; depois escolha o que baixar.
      </p>

      <FeedsAddForm
        newUrl={f.newUrl}
        setNewUrl={f.setNewUrl}
        contentType={f.contentType}
        setContentType={f.setContentType}
        adding={f.adding}
        addError={f.addError}
        onAddFeed={f.handleAddFeed}
      />

      {f.fetchError && (
        <div className="atum-feeds-error" role="alert">
          <span>{f.fetchError}</span>{' '}
          <button type="button" className="atum-btn atum-btn-small" onClick={() => { f.refetchFeeds(); f.refetchPending(); }}>
            Tentar novamente
          </button>
        </div>
      )}

      <FeedsAISection
        aiOpen={f.aiOpen}
        aiLoading={f.aiLoading}
        aiSuggestions={f.aiSuggestions}
        onFetch={f.fetchAIFeedSuggestions}
        onAddSuggested={f.addSuggestedFeed}
      />

      <FeedsList feeds={f.feeds} loading={f.loading} onRemove={f.handleRemoveFeed} />

      <section className="atum-feeds-actions">
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          onClick={f.handlePoll}
          disabled={f.polling || f.feeds.length === 0}
        >
          {f.polling ? 'Verificando…' : 'Verificar feeds agora'}
        </button>
      </section>

      <FeedsPendingSection
        pending={f.pending}
        pendingLoading={f.pendingLoading}
        feedsReconnecting={f.feedsReconnecting}
        selectedPending={f.selectedPending}
        organize={f.organize}
        setOrganize={f.setOrganize}
        addToDownloadsRunning={f.addToDownloadsRunning}
        onTogglePending={f.togglePending}
        onSelectAll={f.selectAllPending}
        onAddToDownloads={f.handleAddToDownloads}
      />
    </div>
  );
}
