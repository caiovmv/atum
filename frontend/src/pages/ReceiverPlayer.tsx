import { lazy, Suspense } from 'react';
import { IoSparkles } from 'react-icons/io5';
import { ReceiverPanel } from '../components/receiver/ReceiverPanel';
import { ReceiverMobile } from '../components/receiver/ReceiverMobile';
import { ReceiverSidePanel } from '../components/receiver/ReceiverSidePanel';
import { ReceiverSidePanelContent } from '../components/receiver/ReceiverSidePanelContent';
import { BottomSheet } from '../components/BottomSheet';
import { ReceiverEngineProvider } from '../contexts/ReceiverEngineContext';
import { useReceiverPlayer } from '../hooks/useReceiverPlayer';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { usePiP } from '../hooks/usePiP';
import { useNowPlaying } from '../contexts/NowPlayingContext';
import { SkeletonPlayer } from '../components/Skeleton';
import './Player.css';

const AudioVisualizerOverlay = lazy(() =>
  import('../components/receiver/AudioVisualizer/AudioVisualizerOverlay').then((m) => ({
    default: m.AudioVisualizerOverlay,
  }))
);

function TransportBackButton({ onClick, className }: { onClick: () => void; className?: string }) {
  return (
    <button
      type="button"
      className={className ?? 'receiver-mobile-transport-btn'}
      onClick={onClick}
      aria-label="Voltar"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
    </button>
  );
}

export function ReceiverPlayer() {
  const rp = useReceiverPlayer();
  const nowPlaying = useNowPlaying();
  const isMobile = useMediaQuery('(max-width: 599px)');
  usePiP(rp.isVideo ? '.receiver-video-player' : '.no-pip-target');

  if (rp.loading) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <SkeletonPlayer />
      </div>
    );
  }

  if (rp.error || !rp.item) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <div className="receiver-mobile-transport" style={{ marginBottom: '1rem' }}>
          <TransportBackButton onClick={rp.goBack} />
        </div>
        <p className="atum-player-error">{rp.error || 'Item não encontrado.'}</p>
      </div>
    );
  }

  if (rp.files.length === 0) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <div className="receiver-mobile-transport" style={{ marginBottom: '1rem' }}>
          <TransportBackButton onClick={rp.goBack} />
        </div>
        <h1 className="atum-player-title">{rp.item.name || 'Reproduzir'}</h1>
        <p className="atum-player-error">Nenhum arquivo de mídia encontrado neste download.</p>
      </div>
    );
  }

  const artist = rp.ctxTrack?.artist || (rp.isRadio && rp.radioQueue?.[rp.activeRadioQueueIndex]?.artist ? rp.radioQueue[rp.activeRadioQueueIndex].artist : undefined);
  const qualityMetaFormatted = rp.qualityMeta ? { codec: rp.qualityMeta.codec, bitrate: rp.qualityMeta.bitrate != null ? `${rp.qualityMeta.bitrate} kbps` : undefined } : null;

  return (
    <ReceiverEngineProvider engine={rp.receiverEngine}>
      <div className="atum-player atum-player--fullscreen">
        <div className="receiver-layout">
          {rp.isVideo ? (
            <div className="receiver-video-main">
              <video
                key={rp.streamUrl}
                className="receiver-video-player"
                controls
                autoPlay
                playsInline
                src={rp.streamUrl}
              >
                Seu navegador não suporta vídeo.
              </video>
              <div className="receiver-video-title">
                <span className="receiver-video-title-label">{rp.title}</span>
                <div className="receiver-video-controls-row">
                  <TransportBackButton onClick={rp.goBack} className="receiver-video-nav-btn receiver-video-nav-btn--icon" />
                  {rp.hasPrev && (
                    <button type="button" className="receiver-video-nav-btn" onClick={nowPlaying.goPrev}>
                      ⏮ Anterior
                    </button>
                  )}
                  {rp.hasNext && (
                    <button type="button" className="receiver-video-nav-btn" onClick={nowPlaying.goNext}>
                      Próximo ⏭
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : isMobile ? (
            <ReceiverMobile
              streamUrl={rp.streamUrl}
              title={rp.title}
              contentType={rp.item?.content_type ?? null}
              itemId={rp.item!.id}
              isImport={!!rp.isImport}
              hasPrev={rp.hasPrev}
              hasNext={rp.hasNext}
              onBack={rp.goBack}
              onPrev={nowPlaying.goPrev}
              onNext={nowPlaying.goNext}
              onEngineReady={rp.handleEngineReady}
              onTimeUpdate={nowPlaying.updateTime}
              onDurationChange={nowPlaying.updateDuration}
              onPlayingChange={nowPlaying.updatePlaying}
              onMenuOpen={() => rp.setSideOpen(true)}
            />
          ) : (
            <ReceiverPanel
              streamUrl={rp.streamUrl}
              title={rp.title}
              fileName={rp.currentFile?.name}
              contentType={rp.item?.content_type ?? null}
              artist={artist}
              album={rp.item?.name}
              coverUrl={rp.item ? (rp.isImport ? `/api/cover/file/import/${rp.item.id}` : `/api/cover/file/${rp.item.id}`) : undefined}
              onBack={rp.goBack}
              onNext={nowPlaying.goNext}
              onPrev={nowPlaying.goPrev}
              hasNext={rp.hasNext}
              hasPrev={rp.hasPrev}
              className="receiver-layout-main"
              onSmartQueue={rp.handleSmartQueue}
              onNavigate={(path) => rp.navigate(path)}
              onTimeUpdate={nowPlaying.updateTime}
              onDurationChange={nowPlaying.updateDuration}
              onPlayingChange={nowPlaying.updatePlaying}
              onEngineReady={rp.handleEngineReady}
              audioRef={nowPlaying.audioRef}
            />
          )}

          {!isMobile && (
            <>
              <button
                type="button"
                className={`receiver-side-toggle${rp.sideOpen ? ' receiver-side-toggle--open' : ''}`}
                onClick={() => rp.setSideOpen((p) => !p)}
                aria-label={rp.sideOpen ? 'Fechar painel' : 'Abrir painel'}
              >
                {rp.sideOpen ? '›' : '‹'}
              </button>

              <div
                className={`receiver-bottom-overlay${rp.sideOpen ? ' receiver-bottom-overlay--visible' : ''}`}
                onClick={() => rp.setSideOpen(false)}
              />

              <button
                type="button"
                className="receiver-bottom-sheet-fab"
                onClick={() => rp.setSideOpen((p) => !p)}
                aria-label="Abrir detalhes"
              >
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path d="M3 4h14v2H3zM3 9h14v2H3zM3 14h10v2H3z" />
                </svg>
              </button>
            </>
          )}

          {!rp.isVideo && !isMobile && (
            <button
              type="button"
              className="receiver-visualizer-fab"
              onClick={() => rp.setShowVisualizer(true)}
              aria-label="Abrir visualizador de áudio"
              title="Visualizador"
            >
              <IoSparkles size={22} />
            </button>
          )}

          {isMobile ? (
            <BottomSheet
              open={rp.sideOpen}
              onClose={() => rp.setSideOpen(false)}
              title="Detalhes"
              showCloseButton
            >
              <ReceiverSidePanelContent
                item={rp.item!}
                files={rp.files}
                isImport={!!rp.isImport}
                isRadio={!!rp.isRadio}
                radioQueue={rp.radioQueue}
                activeRadioQueueIndex={rp.activeRadioQueueIndex}
                safeFileIndex={rp.safeFileIndex}
                currentFile={rp.currentFile}
                qualityMeta={qualityMetaFormatted}
                trackFavorited={!!rp.trackFavorited}
                onToggleFav={rp.handleToggleFav}
                rpPlaylistOpen={rp.rpPlaylistOpen}
                setRpPlaylistOpen={rp.setRpPlaylistOpen}
                rpPlaylists={rp.rpPlaylists}
                rpPlaylistRef={rp.rpPlaylistRef}
                onAddToPlaylist={rp.handleAddToPlaylist}
                savingQueue={rp.savingQueue}
                onSaveQueueAsPlaylist={rp.handleSaveQueueAsPlaylist}
                goToQueueTrack={rp.goToQueueTrack}
                goToFileTrack={rp.goToFileTrack}
                aiInsight={rp.aiInsight}
                aiLoading={rp.aiLoading}
                onFetchAiInsight={rp.fetchAiInsight}
              />
            </BottomSheet>
          ) : (
            <ReceiverSidePanel
            item={rp.item}
            files={rp.files}
            isImport={!!rp.isImport}
            isRadio={!!rp.isRadio}
            radioQueue={rp.radioQueue}
            activeRadioQueueIndex={rp.activeRadioQueueIndex}
            safeFileIndex={rp.safeFileIndex}
            currentFile={rp.currentFile}
            qualityMeta={qualityMetaFormatted}
            trackFavorited={!!rp.trackFavorited}
            onToggleFav={rp.handleToggleFav}
            rpPlaylistOpen={rp.rpPlaylistOpen}
            setRpPlaylistOpen={rp.setRpPlaylistOpen}
            rpPlaylists={rp.rpPlaylists}
            rpPlaylistRef={rp.rpPlaylistRef}
            onAddToPlaylist={rp.handleAddToPlaylist}
            savingQueue={rp.savingQueue}
            onSaveQueueAsPlaylist={rp.handleSaveQueueAsPlaylist}
            goToQueueTrack={rp.goToQueueTrack}
            goToFileTrack={rp.goToFileTrack}
            aiInsight={rp.aiInsight}
            aiLoading={rp.aiLoading}
            onFetchAiInsight={rp.fetchAiInsight}
            sideOpen={rp.sideOpen}
            sheetRef={rp.sheetRef}
            onSheetTouchStart={rp.handleSheetTouchStart}
            onSheetTouchMove={rp.handleSheetTouchMove}
            onSheetTouchEnd={rp.handleSheetTouchEnd}
          />
          )}
        </div>

        {rp.showVisualizer && (
          <Suspense
            fallback={
              <div className="atum-player atum-player--fullscreen" style={{ zIndex: 10000 }}>
                <SkeletonPlayer />
              </div>
            }
          >
            <AudioVisualizerOverlay onClose={() => rp.setShowVisualizer(false)} />
          </Suspense>
        )}
      </div>
    </ReceiverEngineProvider>
  );
}
