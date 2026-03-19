import type React from 'react';
import { ReceiverSlider } from './ReceiverSlider';
import { ReceiverToggle } from './ReceiverToggle';
import { SmartEQ } from './SmartEQ';

function balanceDisplay(v: number): string {
  if (v === 0) return 'C';
  return v < 0 ? `L${Math.abs(v)}` : `R${v}`;
}

function toneDisplay(v: number): string {
  if (v === 0) return '0';
  return v > 0 ? `+${v}` : `${v}`;
}

interface ReceiverStackControlsProps {
  volume: number;
  setVolume: (v: number) => void;
  balance: number;
  setBalance: (v: number) => void;
  bass: number;
  mid: number;
  treble: number;
  onBass: (v: number) => void;
  onMid: (v: number) => void;
  onTreble: (v: number) => void;
  loudness: boolean;
  setLoudness: React.Dispatch<React.SetStateAction<boolean>>;
  att: boolean;
  setAtt: React.Dispatch<React.SetStateAction<boolean>>;
  smartEqActive: boolean;
  setSmartEqActive: React.Dispatch<React.SetStateAction<boolean>>;
  fftData: Uint8Array;
  sampleRate: number;
  audioCtx: AudioContext | null;
  onApplyCorrection: (gains: number[]) => void;
  onApplyPreset: (gains: number[]) => void;
  onCorrectionPreview: (gains: number[] | null) => void;
}

export function ReceiverStackControls({
  volume,
  setVolume,
  balance,
  setBalance,
  bass,
  mid,
  treble,
  onBass,
  onMid,
  onTreble,
  loudness,
  setLoudness,
  att,
  setAtt,
  smartEqActive,
  setSmartEqActive,
  fftData,
  sampleRate,
  audioCtx,
  onApplyCorrection,
  onApplyPreset,
  onCorrectionPreview,
}: ReceiverStackControlsProps) {
  return (
    <div className="receiver-stack-controls">
      <div className="receiver-controls-row">
        <div className="receiver-controls-cluster receiver-controls-cluster--sliders">
          <ReceiverSlider
            value={volume}
            min={0}
            max={100}
            onChange={setVolume}
            label="VOLUME"
            displayValue={`${Math.round(volume)}%`}
          />
          <ReceiverSlider
            value={balance}
            min={-50}
            max={50}
            onChange={(v) => setBalance(Math.round(v))}
            label="BALANCE"
            displayValue={balanceDisplay(Math.round(balance))}
          />
        </div>
        <div className="receiver-controls-cluster receiver-controls-cluster--sliders">
          <ReceiverSlider
            value={bass}
            min={-6}
            max={6}
            onChange={onBass}
            label="BASS"
            displayValue={toneDisplay(bass)}
          />
          <ReceiverSlider
            value={mid}
            min={-6}
            max={6}
            onChange={onMid}
            label="MID"
            displayValue={toneDisplay(mid)}
          />
          <ReceiverSlider
            value={treble}
            min={-6}
            max={6}
            onChange={onTreble}
            label="TREBLE"
            displayValue={toneDisplay(treble)}
          />
        </div>
        <div className="receiver-controls-cluster">
          <ReceiverToggle active={loudness} onToggle={() => setLoudness((p) => !p)} label="LOUDNESS" />
          <ReceiverToggle active={att} onToggle={() => setAtt((p) => !p)} label="ATT -20dB" />
          <ReceiverToggle active={smartEqActive} onToggle={() => setSmartEqActive((p) => !p)} label="SMART EQ" />
        </div>
      </div>
      <div className={`smarteq-panel-wrap${smartEqActive ? ' smarteq-panel-wrap--open' : ''}`}>
        <SmartEQ
          fftData={fftData}
          sampleRate={sampleRate}
          audioCtx={audioCtx}
          onApplyCorrection={onApplyCorrection}
          onApplyPreset={onApplyPreset}
          onCorrectionPreview={onCorrectionPreview}
          active={smartEqActive}
        />
      </div>
    </div>
  );
}
