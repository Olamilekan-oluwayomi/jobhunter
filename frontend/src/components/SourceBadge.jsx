import Badge from "./ui/Badge";

const SOURCE_VARIANTS = {
  Remotive: "accent",
  RemoteOK: "info",
  Jobicy: "success",
  Arbeitnow: "warning",
  Reddit: "danger",
  Upwork: "muted",
};

export default function SourceBadge({ source, className = "" }) {
  return (
    <Badge variant={SOURCE_VARIANTS[source] ?? "muted"} className={className}>
      {source}
    </Badge>
  );
}