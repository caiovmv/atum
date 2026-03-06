import type { ReactNode } from 'react';
import './EmptyState.css';

export interface EmptyStateProps {
  /** Ícone ou ilustração (ex.: emoji ou componente) */
  icon?: ReactNode;
  /** Título principal */
  title: string;
  /** Descrição opcional */
  description?: string;
  /** Ação opcional (link ou botão) */
  action?: ReactNode;
  /** Classe adicional no container */
  className?: string;
}

export function EmptyState({ icon, title, description, action, className = '' }: EmptyStateProps) {
  return (
    <div className={`empty-state ${className}`.trim()} role="status">
      {icon != null && <div className="empty-state-icon" aria-hidden>{icon}</div>}
      <h2 className="empty-state-title">{title}</h2>
      {description != null && description !== '' && (
        <p className="empty-state-description">{description}</p>
      )}
      {action != null && <div className="empty-state-action">{action}</div>}
    </div>
  );
}
