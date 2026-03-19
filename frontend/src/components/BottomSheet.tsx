import { useRef, useCallback, useEffect, type ReactNode } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';
import './BottomSheet.css';

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  showCloseButton?: boolean;
  children: ReactNode;
}

export function BottomSheet({ open, onClose, title, showCloseButton, children }: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef<number | null>(null);
  const dragOffsetRef = useRef(0);

  useFocusTrap(sheetRef, open);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    dragStartY.current = e.touches[0].clientY;
    dragOffsetRef.current = 0;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (dragStartY.current == null) return;
    const dy = e.touches[0].clientY - dragStartY.current;
    if (dy < 0) return;
    dragOffsetRef.current = dy;
    const el = sheetRef.current;
    if (el) el.style.transform = `translateY(${dy}px)`;
  }, []);

  const handleTouchEnd = useCallback(() => {
    dragStartY.current = null;
    const el = sheetRef.current;
    if (dragOffsetRef.current > 100) {
      onClose();
    }
    if (el) el.style.transform = '';
    dragOffsetRef.current = 0;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="bottom-sheet-overlay" onClick={onClose} role="presentation">
      <div
        ref={sheetRef}
        className="bottom-sheet"
        onClick={e => e.stopPropagation()}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Painel'}
      >
        <div className="bottom-sheet-handle" aria-hidden />
        {(title || showCloseButton) && (
          <div className="bottom-sheet-header">
            {title && <div className="bottom-sheet-title">{title}</div>}
            {showCloseButton && (
              <button
                type="button"
                className="bottom-sheet-close"
                onClick={onClose}
                aria-label="Fechar"
              >
                ×
              </button>
            )}
          </div>
        )}
        <div className="bottom-sheet-content">
          {children}
        </div>
      </div>
    </div>
  );
}
