import { X } from "lucide-react";

export default function FilterChip({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm border border-line bg-raised px-2 py-0.5 text-xs font-medium text-ink-secondary">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
        className="text-ink-faint transition-colors hover:text-ink"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}