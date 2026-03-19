import { VuMeter } from './VuMeter';
import { PowerMeter } from './PowerMeter';

interface ReceiverStackMetersProps {
  vuL: number;
  vuR: number;
  peak: number;
}

export function ReceiverStackMeters({ vuL, vuR, peak }: ReceiverStackMetersProps) {
  return (
    <div className="receiver-stack-meters">
      <div className="receiver-stack-glass">
        <div className="receiver-row-meters">
          <div className="receiver-meters-lr">
            <VuMeter value={vuL} label="dBLevel L" meterIndex={0} />
            <VuMeter value={vuR} label="dBLevel R" meterIndex={1} />
          </div>
          <PowerMeter value={peak} />
        </div>
      </div>
    </div>
  );
}
