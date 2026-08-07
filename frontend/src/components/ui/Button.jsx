const VARIANTS = {
  primary: "bg-accent text-[#00110d] hover:bg-accent-hover",
  secondary:
    "border border-line bg-raised text-ink hover:border-line-strong hover:bg-inset",
  outline:
    "border border-line-strong bg-transparent text-ink-secondary hover:bg-line hover:text-ink",
  ghost: "bg-transparent text-ink-secondary hover:bg-line hover:text-ink",
  danger: "bg-danger-soft text-danger hover:bg-danger/20",
};

const SIZES = {
  sm: "h-8 px-3 text-sm",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-5 text-sm",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:pointer-events-none disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}