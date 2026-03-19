/** Componentes reutilizáveis do formulário de configurações */

import { Input } from '../Input';

export function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="atum-settings-toggle-wrap">
      <div className="atum-settings-toggle-info">
        <div className="atum-settings-label">{label}</div>
        {hint && <div className="atum-settings-hint">{hint}</div>}
      </div>
      <label className="atum-settings-toggle" aria-label={label}>
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
        <span className="atum-settings-toggle-track" />
      </label>
    </div>
  );
}

export function Field({
  label,
  hint,
  type = 'text',
  value,
  onChange,
  placeholder,
  children,
}: {
  label: string;
  hint?: string;
  type?: string;
  value?: string;
  onChange?: (v: string) => void;
  placeholder?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="atum-settings-field">
      <span className="atum-settings-label">{label}</span>
      {hint && <span className="atum-settings-hint">{hint}</span>}
      {children ?? (
        <Input
          type={type}
          value={value ?? ''}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
        />
      )}
    </div>
  );
}
