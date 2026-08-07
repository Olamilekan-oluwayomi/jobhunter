import Skeleton from "./ui/Skeleton";

export default function PageLoader() {
  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      <Skeleton className="h-8 w-56" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="hidden h-28 md:block" />
      </div>
      <Skeleton className="h-72" />
    </div>
  );
}