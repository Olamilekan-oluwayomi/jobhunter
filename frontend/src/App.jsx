import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import PageLoader from "./components/PageLoader";

const Workspace = lazy(() => import("./Workspace"));

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Workspace />} />
        <Route
          path="/jobs"
          element={<Navigate to="/?view=explore" replace />}
        />
        <Route path="/preview" element={<Navigate to="/" replace />} />
        <Route path="/saved" element={<Navigate to="/?view=saved" replace />} />
        <Route
          path="/applications"
          element={<Navigate to="/?view=applications" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
