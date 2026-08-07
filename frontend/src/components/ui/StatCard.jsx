import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import Card from "./Card";

const TREND_ICONS = {
  up: TrendingUp,
  down: TrendingDown,
  neutral: Minus,
};

const TREND_TONE = {
  up: "text-success",
  down: "text-warning",
  neutral: "text-ink-muted",
};

const TREND_BG = {
  up: "bg-success-soft",
  down: "bg-warning-soft",
  neutral: "bg-muted-soft",
};

export default function StatCard({
  icon,
  label,
  value,
  sub,
  trend,
  trendTone = "neutral",
}) {
  const TrendIcon = trend ? TREND_ICONS[trendTone] : null;

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-accent-soft text-accent">
          {icon}
        </div>
        {trend && TrendIcon && (
          <span
            className={`inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-xs font-medium ${TREND_BG[trendTone]} ${TREND_TONE[trendTone]}`}
          >
            <TrendIcon className="h-3 w-3" />
            {trend}
          </span>
        )}
      </div>

      <p className="mt-3 text-sm font-medium text-ink-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight text-ink tabular-nums">
        {value}
      </p>

      {sub && <p className="mt-1 text-xs text-ink-muted">{sub}</p>}
    </Card>
  );
}