import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: 'default' | 'small';
  variant?: 'default' | 'ghost';
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { size = 'default', variant = 'default', className = '', ...props },
  ref
) {
  return (
    <input
      ref={ref}
      className={`atum-input ${size === 'small' ? 'atum-input--small' : ''} ${variant === 'ghost' ? 'atum-input--ghost' : ''} ${className}`.trim()}
      {...props}
    />
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  size?: 'default' | 'small';
}

export function Textarea({ size = 'default', className = '', ...props }: TextareaProps) {
  return (
    <textarea
      className={`atum-input atum-input-textarea ${size === 'small' ? 'atum-input--small' : ''} ${className}`.trim()}
      {...props}
    />
  );
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  size?: 'default' | 'small';
}

export function Select({ size = 'default', className = '', children, ...props }: SelectProps) {
  return (
    <select
      className={`atum-select ${size === 'small' ? 'atum-input--small' : ''} ${className}`.trim()}
      {...props}
    >
      {children}
    </select>
  );
}
