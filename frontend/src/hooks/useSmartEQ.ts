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
} from '../audio/spectralEQ';
import { RoomEQSession, type RoomEQPhase } from '../audio/roomEQ';

export type SmartEQMode = 'idle' | 'analyzing' | 'done';

interface UseSmartEQProps {
  fftData: Uint8Array;
  sampleRate: number;
  audioCtx: AudioContext | null;
  onApplyCorrection: (gains: number[]) => void;
  onApplyPreset: (gains: number[]) => void;
  onCorrectionPreview: (gains: number[] | null) => void;
}

export function useSmartEQ({
  fftData,
  sampleRate,
  audioCtx,
  onApplyCorrection,
  onApplyPreset,
  onCorrectionPreview,
}: UseSmartEQProps) {
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

  return {
    mode,
    progress,
    result,
    selectedCurve,
    allCurves,
    showPresets,
    setShowPresets,
    capturingRef,
    refProgress,
    refTracks,
    roomPhase,
    roomProgress,
    roomResult,
    roomError,
    handleStartAnalysis,
    handleStopAnalysis,
    handleApply,
    handlePreset,
    handleCurveChange,
    handleStartRefCapture,
    handleStopRefCapture,
    handleDeleteRef,
    handleRoomStart,
    handleRoomStop,
    handleRoomApply,
    handleRoomRetry,
  };
}
