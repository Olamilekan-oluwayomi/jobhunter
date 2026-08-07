import { companyInitials } from "../utils/jobMeta";

const SIZES = {
  sm: "h-8 w-8 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-11 w-11 text-base",
};

export default function CompanyLogo({ company, size = "md" }) {
  return (
    <div
      className={`flex shrink-0 select-none items-center justify-center rounded-sm border border-line bg-raised font-semibold text-ink-secondary ${SIZES[size]}`}
      aria-hidden="true"
    >
      {companyInitials(company)}
    </div>
  );
}