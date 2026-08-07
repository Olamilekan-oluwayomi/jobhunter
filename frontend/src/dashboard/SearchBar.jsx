import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import Input from "../components/ui/Input";

export default function SearchBar({
  onQuery,
  placeholder = "Search jobs, companies, locations…",
}) {
  const [value, setValue] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => onQuery(value), 250);
    return () => clearTimeout(timer);
  }, [value, onQuery]);

  const normalized = useMemo(() => value.trim().toLowerCase(), [value]);

  return (
    <div className="relative max-w-2xl">
      <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-muted" />
      <Input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        className="pl-9"
        aria-label="Search jobs"
      />
      {normalized && (
        <span className="absolute top-1/2 right-3 -translate-y-1/2 rounded-sm bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-hover">
          Matching…
        </span>
      )}
    </div>
  );
}