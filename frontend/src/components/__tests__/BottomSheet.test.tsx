import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BottomSheet } from '../BottomSheet';

describe('BottomSheet', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <BottomSheet open={false} onClose={() => {}}>
        <p>conteúdo</p>
      </BottomSheet>,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders children when open', () => {
    render(
      <BottomSheet open={true} onClose={() => {}} title="Teste">
        <p>conteúdo visível</p>
      </BottomSheet>,
    );
    expect(screen.getByText('conteúdo visível')).toBeInTheDocument();
    expect(screen.getByText('Teste')).toBeInTheDocument();
  });

  it('calls onClose when overlay is clicked', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open={true} onClose={onClose}>
        <p>conteúdo</p>
      </BottomSheet>,
    );
    fireEvent.click(document.querySelector('.bottom-sheet-overlay')!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose on Escape key', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open={true} onClose={onClose}>
        <p>conteúdo</p>
      </BottomSheet>,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not close when clicking inside the sheet', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open={true} onClose={onClose}>
        <p>conteúdo</p>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByText('conteúdo'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('has correct ARIA attributes', () => {
    render(
      <BottomSheet open={true} onClose={() => {}} title="Meu Painel">
        <p>conteúdo</p>
      </BottomSheet>,
    );
    const dialog = screen.getByRole('dialog', { hidden: true });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label', 'Meu Painel');
  });
});
