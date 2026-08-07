import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import PageLoader from "./components/PageLoader";

const DashboardPage = lazy(() => import("./pages/Dashboard"));
const JobsPage = lazy(() => import("./pages/Jobs"));

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}