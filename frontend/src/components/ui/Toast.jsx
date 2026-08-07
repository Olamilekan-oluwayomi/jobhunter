/* oxlint-disable react/only-export-components -- hook + provider in one file */
import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

const ToastContext = createContext(null);

const ICONS = {
  success: CheckCircle2,
  info: Info,
  danger: TriangleAlert,
};

const TONE_CLASSES = {
  success: "text-success",
  info: "text-info",
  danger: "text-danger",
};

const MAX_VISIBLE = 4;

function ToastItem({ toast, onDismiss }) {
  const Icon = ICONS[toast.tone] ?? Info;

  return (
    <div
      role="status"
      className="pointer-events-auto flex items-start gap-2.5 rounded-md border border-line bg-surface p-3 shadow-popover motion-safe:animate-toast-in"
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${TONE_CLASSES[toast.tone] ?? "text-ink-muted"}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{toast.title}</p>
        {toast.description && (
          <p className="mt-0.5 text-xs text-ink-muted">{toast.description}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        className="shrink-0 rounded-sm p-0.5 text-ink-faint transition-colors hover:text-ink"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (title, options = {}) => {
      const id = ++nextId.current;
      const toast = {
        id,
        title,
        description: options.description ?? "",
        tone: options.tone ?? "success",
      };
      setToasts((prev) => [...prev.slice(-(MAX_VISIBLE - 1)), toast]);
      if (options.autoDismiss !== false) {
        setTimeout(() => dismiss(id), options.duration ?? 3500);
      }
      return id;
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed top-4 right-4 z-50 flex w-80 flex-col gap-2"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
};