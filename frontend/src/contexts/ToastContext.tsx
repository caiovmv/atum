import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ToastList } from '../components/ToastList';

export interface ToastItem {
  id: number;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  showToast: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextIdRef = useRef(0);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  const showToast = useCallback((message: string, duration = 4000) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, message, duration }]);
    if (duration > 0) {
      const timer = setTimeout(() => {
        timersRef.current.delete(id);
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
      timersRef.current.set(id, timer);
    }
  }, []);

  const dismiss = useCallback((id: number) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastList toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      showToast: (message: string) => {
        console.warn('ToastProvider not mounted, message:', message);
      },
    };
  }
  return ctx;
}
