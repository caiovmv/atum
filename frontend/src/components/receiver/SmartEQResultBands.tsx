interface SmartEQResultBandsProps {
  gains: number[];
}

export function SmartEQResultBands({ gains }: SmartEQResultBandsProps) {
  return (
    <div className="smarteq-result">
      {gains.map((g, i) => (
        <div key={i} className="smarteq-result-band">
          <span className={`smarteq-result-val${g > 0 ? ' smarteq-result-val--pos' : g < 0 ? ' smarteq-result-val--neg' : ''}`}>
            {g > 0 ? `+${g}` : g}
          </span>
        </div>
      ))}
    </div>
  );
}
