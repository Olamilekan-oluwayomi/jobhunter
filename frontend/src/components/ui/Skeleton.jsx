export default function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-sm bg-skeleton ${className}`} />;
}

export function SkeletonRow() {
  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3.5 w-2/3" />
        <Skeleton className="h-3 w-1/3" />
      </div>
      <Skeleton className="h-5 w-14" />
    </div>
  );
}

export function SkeletonStat() {
  return (
    <div className="space-y-3 p-5">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-3 w-20" />
    </div>
  );
}