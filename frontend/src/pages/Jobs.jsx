import JobsExplorer from "../jobs/JobsExplorer";
import DashboardLayout from "../layout/DashboardLayout";

export default function JobsPage() {
  return (
    <DashboardLayout>
      <JobsExplorer />
    </DashboardLayout>
  );
}