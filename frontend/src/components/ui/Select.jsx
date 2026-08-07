const CHEVRON_DATA_URI =
  "data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23a0a6b1%22%20stroke-width%3D%222.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22%2F%3E%3C%2Fsvg%3E";

export default function Select({ className = "", children, ...props }) {
  return (
    <select
      className={`h-9 w-full cursor-pointer appearance-none rounded-sm border border-line-strong bg-inset bg-no-repeat pr-8 pl-3 text-sm text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 ${className}`}
      style={{
        backgroundImage: `url("${CHEVRON_DATA_URI}")`,
        backgroundPosition: "right 0.5rem center",
      }}
      {...props}
    >
      {children}
    </select>
  );
}