import { ChevronLeft, ChevronRight } from "lucide-react";

import Button from "../components/ui/Button";

function pageWindow(current, total) {
  const size = 5;
  const start = Math.max(1, Math.min(current - Math.floor(size / 2), total - size + 1));
  return Array.from({ length: Math.min(size, total) }, (_, i) => start + i);
}

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  return (
    <nav
      className="flex items-center justify-center gap-1.5"
      aria-label="Pagination"
    >
      <Button
        variant="outline"
        size="sm"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {pageWindow(page, totalPages).map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onPageChange(p)}
          aria-current={p === page ? "page" : undefined}
          className={`h-8 min-w-8 rounded-sm px-2 text-sm font-medium transition-colors duration-150 tabular-nums ${
            p === page
              ? "bg-accent text-[#00110d]"
              : "text-ink-secondary hover:bg-line hover:text-ink"
          }`}
        >
          {p}
        </button>
      ))}

      <Button
        variant="outline"
        size="sm"
        disabled={page === totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </nav>
  );
}