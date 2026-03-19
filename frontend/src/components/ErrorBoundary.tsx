import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="error-boundary">
        <div className="error-boundary-card">
          <div className="error-boundary-icon" aria-hidden>⚠</div>
          <h1 className="error-boundary-title">Algo deu errado</h1>
          <p className="error-boundary-message">
            {this.state.error?.message || 'Erro inesperado na aplicação.'}
          </p>
          <div className="error-boundary-actions">
            <button type="button" className="error-boundary-btn error-boundary-btn--primary" onClick={this.handleReload}>
              Recarregar página
            </button>
            <button type="button" className="error-boundary-btn" onClick={this.handleReset}>
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }
}
