export default function Input({ className = "", ...props }) {
  return (
    <input
      className={`h-9 w-full rounded-sm border border-line-strong bg-inset px-3 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 ${className}`}
      {...props}
    />
  );
}