import { useState, useCallback, useRef, useEffect } from 'react';
import {
  SpectralAnalyzer,
  TARGET_CURVES,
  referenceToTargetCurve,
  saveReferenceTrack,
  loadReferenceTrackList,
  deleteReferenceTrack,
  type TargetCurve,
  type SpectralResult,
  type ReferenceTrack,
} from '../../audio/spectralEQ';
import { RoomEQSession, type RoomEQPhase } from '../../audio/roomEQ';

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

type SmartEQMode = 'idle' | 'analyzing' | 'done';

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
  const analyzerRef = useRef<SpectralAnalyzer>(new SpectralAnalyzer());
  const [mode, setMode] = useState<SmartEQMode>('idle');
  const [selectedCurve, setSelectedCurve] = useState<TargetCurve>(TARGET_CURVES[0]);
  const [result, setResult] = useState<SpectralResult | null>(null);
  const [progress, setProgress] = useState(0);
  const [showPresets, setShowPresets] = useState(false);
  const [refTracks, setRefTracks] = useState<ReferenceTrack[]>(() => loadReferenceTrackList());
  const [capturingRef, setCapturingRef] = useState(false);
  const refAnalyzerRef = useRef<SpectralAnalyzer>(new SpectralAnalyzer());
  const [refProgress, setRefProgress] = useState(0);

  // Room EQ
  const roomSessionRef = useRef<RoomEQSession | null>(null);
  const [roomPhase, setRoomPhase] = useState<RoomEQPhase>('idle');
  const [roomProgress, setRoomProgress] = useState(0);
  const [roomResult, setRoomResult] = useState<number[] | null>(null);
  const [roomError, setRoomError] = useState<string | null>(null);

  const allCurves: TargetCurve[] = [
    ...TARGET_CURVES,
    ...refTracks.map(referenceToTargetCurve),
  ];

  useEffect(() => {
    if (!capturingRef) return;
    refAnalyzerRef.current.addSnapshot(fftData, sampleRate);
    const count = refAnalyzerRef.current.snapshotCount;
    setRefProgress(Math.min(1, count / 150));
    if (count >= 150) {
      const title = `Track ${new Date().toLocaleTimeString()}`;
      const track = refAnalyzerRef.current.captureAsReference(title);
      saveReferenceTrack(track);
      setRefTracks(loadReferenceTrackList());
      setCapturingRef(false);
      setRefProgress(0);
      refAnalyzerRef.current.reset();
    }
  }, [fftData, sampleRate, capturingRef]);

  useEffect(() => {
    if (mode !== 'analyzing') return;
    analyzerRef.current.addSnapshot(fftData, sampleRate);
    const count = analyzerRef.current.snapshotCount;
    const target = 150;
    setProgress(Math.min(1, count / target));

    if (count >= target) {
      const r = analyzerRef.current.computeCorrection(selectedCurve);
      setResult(r);
      setMode('done');
      onCorrectionPreview(r.correction);
    }
  }, [fftData, sampleRate, mode, selectedCurve, onCorrectionPreview]);

  const handleStartAnalysis = useCallback(() => {
    analyzerRef.current.reset();
    setResult(null);
    setProgress(0);
    setMode('analyzing');
  }, []);

  const handleStopAnalysis = useCallback(() => {
    if (analyzerRef.current.isReady) {
      const r = analyzerRef.current.computeCorrection(selectedCurve);
      setResult(r);
      setMode('done');
      onCorrectionPreview(r.correction);
    } else {
      setMode('idle');
      onCorrectionPreview(null);
    }
  }, [selectedCurve, onCorrectionPreview]);

  const handleApply = useCallback(() => {
    if (result) {
      onApplyCorrection(result.correction);
      onCorrectionPreview(null);
      setMode('idle');
    }
  }, [result, onApplyCorrection, onCorrectionPreview]);

  const handlePreset = useCallback(
    (curve: TargetCurve) => {
      setSelectedCurve(curve);
      onApplyPreset(curve.gains);
      setShowPresets(false);
    },
    [onApplyPreset],
  );

  const handleCurveChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const curve = allCurves.find((c) => c.name === e.target.value);
      if (curve) setSelectedCurve(curve);
    },
    [allCurves],
  );

  const handleStartRefCapture = useCallback(() => {
    refAnalyzerRef.current.reset();
    setRefProgress(0);
    setCapturingRef(true);
  }, []);

  const handleStopRefCapture = useCallback(() => {
    if (refAnalyzerRef.current.isReady) {
      const title = `Track ${new Date().toLocaleTimeString()}`;
      const track = refAnalyzerRef.current.captureAsReference(title);
      saveReferenceTrack(track);
      setRefTracks(loadReferenceTrackList());
    }
    setCapturingRef(false);
    setRefProgress(0);
    refAnalyzerRef.current.reset();
  }, []);

  const handleDeleteRef = useCallback((capturedAt: number) => {
    deleteReferenceTrack(capturedAt);
    setRefTracks(loadReferenceTrackList());
  }, []);

  // Room EQ handlers
  const handleRoomStart = useCallback(() => {
    if (!audioCtx) return;
    const session = new RoomEQSession(audioCtx, () => {
      setRoomPhase(session.phase);
      setRoomProgress(session.progress);
      setRoomError(session.error);
      if (session.result) {
        setRoomResult(session.result.correction);
        onCorrectionPreview(session.result.correction);
      }
    });
    roomSessionRef.current = session;
    session.start();
  }, [audioCtx, onCorrectionPreview]);

  const handleRoomStop = useCallback(() => {
    roomSessionRef.current?.stop();
  }, []);

  const handleRoomApply = useCallback(() => {
    if (roomResult) {
      onApplyCorrection(roomResult);
      onCorrectionPreview(null);
      setRoomPhase('idle');
      setRoomResult(null);
    }
  }, [roomResult, onApplyCorrection, onCorrectionPreview]);

  const handleRoomRetry = useCallback(() => {
    setRoomResult(null);
    setRoomPhase('idle');
    onCorrectionPreview(null);
    handleRoomStart();
  }, [handleRoomStart, onCorrectionPreview]);

  useEffect(() => {
    return () => { roomSessionRef.current?.dispose(); };
  }, []);

  if (!active) return null;

  return (
    <div className={`smarteq ${className}`.trim()}>
      {/* Target Curve Selector */}
      <div className="smarteq-row">
        <span className="smarteq-label">TARGET</span>
        <select
          className="smarteq-select"
          value={selectedCurve.name}
          onChange={handleCurveChange}
        >
          {allCurves.map((c) => (
            <option key={c.name} value={c.name}>{c.label}</option>
          ))}
        </select>
      </div>

      {/* Analyze Button */}
      <div className="smarteq-row">
        {mode === 'idle' && (
          <button type="button" className="smarteq-btn" onClick={handleStartAnalysis}>
            <span className="smarteq-btn-indicator" />
            <span className="smarteq-btn-text">ANALYZE</span>
          </button>
        )}
        {mode === 'analyzing' && (
          <button type="button" className="smarteq-btn smarteq-btn--active" onClick={handleStopAnalysis}>
            <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
            <span className="smarteq-btn-text">ANALYZING {Math.round(progress * 100)}%</span>
          </button>
        )}
        {mode === 'done' && result && (
          <>
            <button type="button" className="smarteq-btn smarteq-btn--apply" onClick={handleApply}>
              <span className="smarteq-btn-indicator smarteq-btn-indicator--ready" />
              <span className="smarteq-btn-text">APPLY</span>
            </button>
            <button type="button" className="smarteq-btn" onClick={handleStartAnalysis}>
              <span className="smarteq-btn-text">RETRY</span>
            </button>
          </>
        )}
      </div>

      {/* Result Preview */}
      {mode === 'done' && result && (
        <div className="smarteq-result">
          {result.correction.map((g, i) => (
            <div key={i} className="smarteq-result-band">
              <span className={`smarteq-result-val${g > 0 ? ' smarteq-result-val--pos' : g < 0 ? ' smarteq-result-val--neg' : ''}`}>
                {g > 0 ? `+${g}` : g}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Presets Quick Access */}
      <div className="smarteq-row">
        <button
          type="button"
          className={`smarteq-btn${showPresets ? ' smarteq-btn--active' : ''}`}
          onClick={() => setShowPresets((p) => !p)}
        >
          <span className="smarteq-btn-indicator" />
          <span className="smarteq-btn-text">PRESETS</span>
        </button>
      </div>

      {showPresets && (
        <div className="smarteq-presets">
          {allCurves.map((c) => (
            <button
              key={c.name}
              type="button"
              className={`smarteq-preset-btn${c.name === selectedCurve.name ? ' smarteq-preset-btn--active' : ''}`}
              onClick={() => handlePreset(c)}
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      {/* Reference Track Matching */}
      <div className="smarteq-separator" />
      <div className="smarteq-row">
        {!capturingRef ? (
          <button type="button" className="smarteq-btn" onClick={handleStartRefCapture}>
            <span className="smarteq-btn-indicator" />
            <span className="smarteq-btn-text">CAPTURE REFERENCE</span>
          </button>
        ) : (
          <button type="button" className="smarteq-btn smarteq-btn--active" onClick={handleStopRefCapture}>
            <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
            <span className="smarteq-btn-text">CAPTURING {Math.round(refProgress * 100)}%</span>
          </button>
        )}
        {capturingRef && (
          <div className="smarteq-progress" style={{ flex: 1 }}>
            <div className="smarteq-progress-fill" style={{ width: `${refProgress * 100}%` }} />
          </div>
        )}
      </div>

      {refTracks.length > 0 && (
        <div className="smarteq-presets">
          {refTracks.map((t) => (
            <div key={t.capturedAt} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <button
                type="button"
                className={`smarteq-preset-btn${selectedCurve.name === `ref-${t.capturedAt}` ? ' smarteq-preset-btn--active' : ''}`}
                onClick={() => handlePreset(referenceToTargetCurve(t))}
              >
                REF: {t.name}
              </button>
              <button
                type="button"
                className="smarteq-preset-btn"
                onClick={() => handleDeleteRef(t.capturedAt)}
                title="Remover"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Room EQ (Microphone) */}
      <div className="smarteq-separator" />
      <div className="smarteq-wizard">
        <div className="smarteq-row">
          <span className="smarteq-label">ROOM EQ</span>
          {roomPhase === 'idle' && (
            <button type="button" className="smarteq-btn" onClick={handleRoomStart}>
              <span className="smarteq-btn-indicator" />
              <span className="smarteq-btn-text">CALIBRATE</span>
            </button>
          )}
          {roomPhase === 'requesting-mic' && (
            <span className="smarteq-ref-status">Aguardando permissao do microfone...</span>
          )}
          {roomPhase === 'measuring' && (
            <>
              <button type="button" className="smarteq-btn smarteq-btn--active" onClick={handleRoomStop}>
                <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
                <span className="smarteq-btn-text">MEASURING {Math.round(roomProgress * 100)}%</span>
              </button>
              <div className="smarteq-progress" style={{ flex: 1 }}>
                <div className="smarteq-progress-fill" style={{ width: `${roomProgress * 100}%` }} />
              </div>
            </>
          )}
          {roomPhase === 'done' && (
            <>
              <button type="button" className="smarteq-btn smarteq-btn--apply" onClick={handleRoomApply}>
                <span className="smarteq-btn-indicator smarteq-btn-indicator--ready" />
                <span className="smarteq-btn-text">APPLY ROOM EQ</span>
              </button>
              <button type="button" className="smarteq-btn" onClick={handleRoomRetry}>
                <span className="smarteq-btn-text">RETRY</span>
              </button>
            </>
          )}
          {roomPhase === 'error' && (
            <>
              <span className="smarteq-result-val smarteq-result-val--neg" style={{ fontSize: '0.5rem' }}>
                {roomError}
              </span>
              <button type="button" className="smarteq-btn" onClick={handleRoomStart}>
                <span className="smarteq-btn-text">RETRY</span>
              </button>
            </>
          )}
        </div>

        {roomPhase === 'idle' && (
          <div className="smarteq-wizard-step">
            Posicione o microfone na posicao de escuta.
            O sistema tocara <strong>pink noise</strong> por ~5s e medira a resposta da sala.
          </div>
        )}

        {roomPhase === 'done' && roomResult && (
          <div className="smarteq-result">
            {roomResult.map((g, i) => (
              <div key={i} className="smarteq-result-band">
                <span className={`smarteq-result-val${g > 0 ? ' smarteq-result-val--pos' : g < 0 ? ' smarteq-result-val--neg' : ''}`}>
                  {g > 0 ? `+${g}` : g}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
