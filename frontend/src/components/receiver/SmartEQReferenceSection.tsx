import { referenceToTargetCurve, type TargetCurve, type ReferenceTrack } from '../../audio/spectralEQ';

interface SmartEQReferenceSectionProps {
  capturingRef: boolean;
  refProgress: number;
  refTracks: ReferenceTrack[];
  selectedCurveName: string;
  onStartCapture: () => void;
  onStopCapture: () => void;
  onPreset: (curve: TargetCurve) => void;
  onDeleteRef: (capturedAt: number) => void;
}

export function SmartEQReferenceSection({
  capturingRef,
  refProgress,
  refTracks,
  selectedCurveName,
  onStartCapture,
  onStopCapture,
  onPreset,
  onDeleteRef,
}: SmartEQReferenceSectionProps) {
  return (
    <>
      <div className="smarteq-separator" />
      <div className="smarteq-row">
        {!capturingRef ? (
          <button type="button" className="smarteq-btn" onClick={onStartCapture}>
            <span className="smarteq-btn-indicator" />
            <span className="smarteq-btn-text">CAPTURE REFERENCE</span>
          </button>
        ) : (
          <button type="button" className="smarteq-btn smarteq-btn--active" onClick={onStopCapture}>
            <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
            <span className="smarteq-btn-text">CAPTURING {Math.round(refProgress * 100)}%</span>
          </button>
        )}
        {capturingRef && (
          <div className="smarteq-progress smarteq-progress--flex">
            <div className="smarteq-progress-fill" style={{ width: `${refProgress * 100}%` }} />
          </div>
        )}
      </div>

      {refTracks.length > 0 && (
        <div className="smarteq-presets">
          {refTracks.map((t) => (
            <div key={t.capturedAt} className="smarteq-ref-track-row">
              <button
                type="button"
                className={`smarteq-preset-btn${selectedCurveName === `ref-${t.capturedAt}` ? ' smarteq-preset-btn--active' : ''}`}
                onClick={() => onPreset(referenceToTargetCurve(t))}
              >
                REF: {t.name}
              </button>
              <button
                type="button"
                className="smarteq-preset-btn"
                onClick={() => onDeleteRef(t.capturedAt)}
                title="Remover"
                aria-label="Remover referência"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
