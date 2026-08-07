import {
  Briefcase,
  CalendarDays,
  CalendarRange,
  FolderHeart,
  Globe2,
  Send,
} from "lucide-react";

import StatCard from "../components/ui/StatCard";
import { SkeletonStat } from "../components/ui/Skeleton";
import { countOnCalendarDay, countWithinDays } from "../utils/format";

function delta(current, previous, suffix) {
  const diff = current - previous;
  if (diff === 0) return "same as prior";
  return `${diff > 0 ? "+" : ""}${diff} ${suffix}`;
}

export default function StatsGrid({ stats, jobs, isLoading }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonStat key={i} />
        ))}
      </div>
    );
  }

  const items = jobs ?? [];

  const today = countOnCalendarDay(items, 0);
  const yesterday = countOnCalendarDay(items, 1);
  const week = countWithinDays(items, 7);
  const prevWeek = Math.max(0, countWithinDays(items, 14) - week);

  const cards = [
    {
      icon: <Briefcase className="h-4 w-4" />,
      label: "Total jobs",
      value: stats?.total_jobs ?? 0,
      sub: "across all sources",
    },
    {
      icon: <CalendarDays className="h-4 w-4" />,
      label: "New today",
      value: today,
      sub: "posted in last 24h",
      trend: delta(today, yesterday, "vs yesterday"),
      trendTone: today >= yesterday ? "up" : "down",
    },
    {
      icon: <CalendarRange className="h-4 w-4" />,
      label: "New this week",
      value: week,
      sub: "last 7 days",
      trend: delta(week, prevWeek, "vs prev. week"),
      trendTone: week >= prevWeek ? "up" : "down",
    },
    {
      icon: <Globe2 className="h-4 w-4" />,
      label: "Sources",
      value: stats?.sources ?? 0,
      sub: "active",
    },
    {
      icon: <FolderHeart className="h-4 w-4" />,
      label: "Saved",
      value: stats?.total_saved ?? 0,
      sub: "bookmarked",
    },
    {
      icon: <Send className="h-4 w-4" />,
      label: "Applications",
      value: stats?.total_applications ?? 0,
      sub: "submitted",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      {cards.map((card) => (
        <StatCard key={card.label} {...card} />
      ))}
    </div>
  );
}