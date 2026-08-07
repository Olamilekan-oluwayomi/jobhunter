/* oxlint-disable react/only-export-components -- shared helpers + component */
import { ChevronDown, Filter, Wifi } from "lucide-react";

import Input from "../components/ui/Input";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import FilterChip from "../components/ui/FilterChip";

const EXPERIENCE_OPTIONS = [
  { value: "", label: "Any experience" },
  { value: "junior", label: "Junior" },
  { value: "mid", label: "Mid level" },
  { value: "senior", label: "Senior" },
];

const FILTER_ORDER = [
  "source",
  "company",
  "location",
  "experience",
  "remoteOnly",
  "salaryMin",
  "salaryMax",
] ;

export const isActiveFilter = (value) =>
  value !== "" && value !== undefined && value !== null && value !== false;

const filterLabel = (key, value) => {
  switch (key) {
    case "source":
      return `Source: ${value}`;
    case "company":
      return `Company: ${value}`;
    case "location":
      return `Location: ${value}`;
    case "experience":
      return EXPERIENCE_OPTIONS.find((o) => o.value === value)?.label ?? value;
    case "remoteOnly":
      return "Remote only";
    case "salaryMin":
      return `Minimum $${value}k`;
    case "salaryMax":
      return `Maximum $${value}k`;
    default:
      return value;
  }
}

export const activeFilterCount = (filters) =>
  FILTER_ORDER.filter((key) => isActiveFilter(filters[key])).length;

export const FilterChips = ({ filters, onRemove }) => {
  const chips = FILTER_ORDER.filter((key) =>
    isActiveFilter(filters[key]),
  ).map((key) => (
    <FilterChip
      key={key}
      label={filterLabel(key, filters[key])}
      onRemove={() => onRemove(key)}
    />
  ));

  return chips.length ? (
    <div className="flex flex-wrap items-center gap-1.5">
      {chips}
      <button
        type="button"
        onClick={() => onRemove("__all__")}
        className="text-xs font-medium text-ink-muted transition-colors hover:text-ink"
      >
        Clear all
      </button>
    </div>
  ) : null;
}

export default function FilterBar({
  filters,
  sources,
  onChange,
  open,
  onToggle,
}) {
  const set = (key, value) => onChange({ ...filters, [key]: value });

  const count = activeFilterCount(filters);

  return (
    <div>
      <div className="flex items-center gap-2">
        <Button
          variant={count ? "secondary" : "outline"}
          size="sm"
          onClick={onToggle}
          aria-expanded={open}
        >
          <Filter className="h-3.5 w-3.5" />
          Filters
          {count > 0 && (
            <span className="rounded-sm bg-accent-soft px-1.5 text-xs font-medium text-accent-hover tabular-nums">
              {count}
            </span>
          )}
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          />
        </Button>
      </div>

      {open && (
        <div className="mt-2 grid grid-cols-1 gap-3 rounded-md border border-line bg-surface p-3 sm:grid-cols-2 lg:grid-cols-4 motion-safe:animate-fade-in">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Source
            </label>
            <Select
              value={filters.source ?? ""}
              onChange={(e) => set("source", e.target.value)}
              aria-label="Filter by source"
            >
              <option value="">All sources</option>
              {sources?.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name} ({s.job_count})
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Experience
            </label>
            <Select
              value={filters.experience ?? ""}
              onChange={(e) => set("experience", e.target.value)}
              aria-label="Filter by experience"
            >
              {EXPERIENCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Company
            </label>
            <Input
              value={filters.company ?? ""}
              onChange={(e) => set("company", e.target.value)}
              placeholder="Acme Inc…"
              aria-label="Filter by company"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Location
            </label>
            <Input
              value={filters.location ?? ""}
              onChange={(e) => set("location", e.target.value)}
              placeholder="Remote, New York…"
              aria-label="Filter by location"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Min salary (k)
            </label>
            <Input
              type="number"
              value={filters.salaryMin ?? ""}
              min={0}
              placeholder="80"
              onChange={(e) =>
                set(
                  "salaryMin",
                  e.target.value ? Number(e.target.value) : undefined,
                )
              }
              aria-label="Minimum salary"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">
              Max salary (k)
            </label>
            <Input
              type="number"
              value={filters.salaryMax ?? ""}
              min={0}
              placeholder="250"
              onChange={(e) =>
                set(
                  "salaryMax",
                  e.target.value ? Number(e.target.value) : undefined,
                )
              }
              aria-label="Maximum salary"
            />
          </div>

          <label className="flex cursor-pointer select-none items-center gap-2 self-end pb-2 text-sm text-ink-secondary">
            <input
              type="checkbox"
              checked={filters.remoteOnly ?? false}
              onChange={(e) => set("remoteOnly", e.target.checked)}
              className="h-4 w-4 rounded-sm border-line-strong bg-inset accent-[var(--color-accent)]"
            />
            <Wifi className="h-4 w-4 text-accent" />
            Remote only
          </label>
        </div>
      )}
    </div>
  );
}