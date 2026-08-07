import { Link, useLocation } from "react-router-dom";
import {
  Briefcase,
  FolderHeart,
  LayoutDashboard,
  Send,
  Sparkles,
  X,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Jobs", to: "/jobs", icon: Briefcase },
  { label: "Saved", to: "/saved", icon: FolderHeart, soon: true },
  { label: "Applications", to: "/applications", icon: Send, soon: true },
];

export default function Sidebar({ open, onClose }) {
  const location = useLocation();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-overlay/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-base transition-transform duration-200 motion-reduce:transition-none lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-line px-5">
          <Link to="/" onClick={onClose} className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-sm border border-accent-line bg-accent-soft text-accent">
              <Sparkles className="h-4 w-4" />
            </div>
            <span className="text-base font-semibold tracking-tight text-ink">
              JobHunter
            </span>
          </Link>

          <button
            className="rounded-sm p-1 text-ink-muted transition-colors hover:text-ink lg:hidden"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-6">
          <p className="px-3 pb-2 text-xs font-medium tracking-wider text-ink-faint uppercase">
            Overview
          </p>
          {NAV_ITEMS.map((item) => {
            const active = item.to === location.pathname;
            const classes = `relative flex w-full items-center gap-3 rounded-sm px-3 py-2 text-sm font-medium transition-colors duration-150 ${
              active
                ? "bg-raised text-ink"
                : "text-ink-secondary hover:bg-raised/60 hover:text-ink"
            }`;

            const content = (
              <>
                {active && (
                  <span className="absolute top-1/2 left-0 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent" />
                )}
                <item.icon
                  className={`h-4 w-4 ${active ? "text-accent" : ""}`}
                />
                {item.label}
                {item.soon && (
                  <span className="ml-auto rounded-sm bg-line px-1.5 py-0.5 text-[10px] font-medium text-ink-faint">
                    Soon
                  </span>
                )}
              </>
            );

            if (item.soon) {
              return (
                <span
                  key={item.label}
                  className={`${classes} cursor-not-allowed opacity-60`}
                  aria-disabled="true"
                >
                  {content}
                </span>
              );
            }

            return (
              <Link
                key={item.label}
                to={item.to}
                onClick={onClose}
                className={classes}
                aria-current={active ? "page" : undefined}
              >
                {content}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-line px-5 py-4">
          <p className="text-xs text-ink-faint">
            JobHunter <span className="text-ink-muted">v1.0.0</span>
          </p>
        </div>
      </aside>
    </>
  );
}