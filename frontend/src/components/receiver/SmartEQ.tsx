import { useSmartEQ } from '../../hooks/useSmartEQ';
import { SmartEQResultBands } from './SmartEQResultBands';
import { SmartEQReferenceSection } from './SmartEQReferenceSection';
import { SmartEQRoomEQ } from './SmartEQRoomEQ';

interface SmartEQProps {
  fftData: Uint8Array;
  sampleRate: number;
  audioCtx: AudioContext | null;
  onApplyCorrection: (gains: number[]) => void;
  onApplyPreset: (gains: number[]) => void;
  onCorrectionPreview: (gains: number[] | null) => void;
  active: boolean;
  className?: string;
}

export function SmartEQ({
  fftData,
  sampleRate,
  audioCtx,
  onApplyCorrection,
  onApplyPreset,
  onCorrectionPreview,
  active,
  className = '',
}: SmartEQProps) {
  const eq = useSmartEQ({
    fftData,
    sampleRate,
    audioCtx,
    onApplyCorrection,
    onApplyPreset,
    onCorrectionPreview,
  });

  if (!active) return null;

  return (
    <div className={`smarteq ${className}`.trim()}>
      <div className="smarteq-row">
        <span className="smarteq-label">TARGET</span>
        <select
          className="smarteq-select"
          value={eq.selectedCurve.name}
          onChange={eq.handleCurveChange}
        >
          {eq.allCurves.map((c) => (
            <option key={c.name} value={c.name}>{c.label}</option>
          ))}
        </select>
      </div>

      <div className="smarteq-row">
        {eq.mode === 'idle' && (
          <button type="button" className="smarteq-btn" onClick={eq.handleStartAnalysis}>
            <span className="smarteq-btn-indicator" />
            <span className="smarteq-btn-text">ANALYZE</span>
          </button>
        )}
        {eq.mode === 'analyzing' && (
          <button type="button" className="smarteq-btn smarteq-btn--active" onClick={eq.handleStopAnalysis}>
            <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
            <span className="smarteq-btn-text">ANALYZING {Math.round(eq.progress * 100)}%</span>
          </button>
        )}
        {eq.mode === 'done' && eq.result && (
          <>
            <button type="button" className="smarteq-btn smarteq-btn--apply" onClick={eq.handleApply}>
              <span className="smarteq-btn-indicator smarteq-btn-indicator--ready" />
              <span className="smarteq-btn-text">APPLY</span>
            </button>
            <button type="button" className="smarteq-btn" onClick={eq.handleStartAnalysis}>
              <span className="smarteq-btn-text">RETRY</span>
            </button>
          </>
        )}
      </div>

      {eq.mode === 'done' && eq.result && (
        <SmartEQResultBands gains={eq.result.correction} />
      )}

      <div className="smarteq-row">
        <button
          type="button"
          className={`smarteq-btn${eq.showPresets ? ' smarteq-btn--active' : ''}`}
          onClick={() => eq.setShowPresets((p) => !p)}
        >
          <span className="smarteq-btn-indicator" />
          <span className="smarteq-btn-text">PRESETS</span>
        </button>
      </div>

      {eq.showPresets && (
        <div className="smarteq-presets">
          {eq.allCurves.map((c) => (
            <button
              key={c.name}
              type="button"
              className={`smarteq-preset-btn${c.name === eq.selectedCurve.name ? ' smarteq-preset-btn--active' : ''}`}
              onClick={() => eq.handlePreset(c)}
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      <SmartEQReferenceSection
        capturingRef={eq.capturingRef}
        refProgress={eq.refProgress}
        refTracks={eq.refTracks}
        selectedCurveName={eq.selectedCurve.name}
        onStartCapture={eq.handleStartRefCapture}
        onStopCapture={eq.handleStopRefCapture}
        onPreset={eq.handlePreset}
        onDeleteRef={eq.handleDeleteRef}
      />

      <div className="smarteq-separator" />
      <SmartEQRoomEQ
        roomPhase={eq.roomPhase}
        roomProgress={eq.roomProgress}
        roomResult={eq.roomResult}
        roomError={eq.roomError}
        onStart={eq.handleRoomStart}
        onStop={eq.handleRoomStop}
        onApply={eq.handleRoomApply}
        onRetry={eq.handleRoomRetry}
      />
    </div>
  );
}
