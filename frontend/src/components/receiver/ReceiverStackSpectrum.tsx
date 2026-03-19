import { Spectrum } from './Spectrum';

interface ReceiverStackSpectrumProps {
  fftData: Uint8Array;
  sampleRate: number;
  showWaveform: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onToggleWaveform: () => void;
}

export function ReceiverStackSpectrum({
  fftData,
  sampleRate,
  showWaveform,
  containerRef,
  onToggleWaveform,
}: ReceiverStackSpectrumProps) {
  return (
    <div className="receiver-stack-spectrum">
      <div className="receiver-stack-glass">
        <Spectrum data={fftData} sampleRate={sampleRate} />
        <div
          className={`receiver-waveform-wrap${showWaveform ? '' : ' receiver-waveform-wrap--hidden'}`}
          ref={containerRef}
        />
        <button
          type="button"
          className={`receiver-waveform-toggle${showWaveform ? ' receiver-waveform-toggle--active' : ''}`}
          onClick={onToggleWaveform}
          aria-label={showWaveform ? 'Ocultar waveform' : 'Mostrar waveform'}
        >
          <span className="receiver-toggle-indicator" />
          <span className="receiver-waveform-toggle-label">WAVEFORM</span>
        </button>
      </div>
    </div>
  );
}
