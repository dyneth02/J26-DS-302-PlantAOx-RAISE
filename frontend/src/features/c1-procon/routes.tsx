import type { RouteObject } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { C1Nav } from "@/features/c1-procon/components/C1Nav";
import { OverviewPage } from "@/features/c1-procon/pages/OverviewPage";
import { DatasetPage } from "@/features/c1-procon/pages/DatasetPage";
import { EmbeddingPage } from "@/features/c1-procon/pages/EmbeddingPage";
import { RetrievalPage } from "@/features/c1-procon/pages/RetrievalPage";
import { ProbePage } from "@/features/c1-procon/pages/ProbePage";
import { ConfoundsPage } from "@/features/c1-procon/pages/ConfoundsPage";
import { LookupPage } from "@/features/c1-procon/pages/LookupPage";
import { EvidencePage } from "@/features/c1-procon/pages/EvidencePage";

function C1Layout() {
  return (
    <div className="space-y-6">
      <C1Nav />
      <Outlet />
    </div>
  );
}

/** Component 01's full route contribution; the shared router only spreads this array in. */
export const c1ProconRoutes: RouteObject[] = [
  {
    path: "c1",
    element: <C1Layout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "dataset", element: <DatasetPage /> },
      { path: "embedding", element: <EmbeddingPage /> },
      { path: "retrieval", element: <RetrievalPage /> },
      { path: "probe", element: <ProbePage /> },
      { path: "confounds", element: <ConfoundsPage /> },
      { path: "lookup", element: <LookupPage /> },
      { path: "evidence", element: <EvidencePage /> },
    ],
  },
];
