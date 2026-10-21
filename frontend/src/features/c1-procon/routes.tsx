import type { RouteObject } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { C1Nav } from "@/features/c1-procon/components/C1Nav";
import { OverviewPage } from "@/features/c1-procon/pages/OverviewPage";
import { DatasetPage } from "@/features/c1-procon/pages/DatasetPage";
import { RetrievalPage } from "@/features/c1-procon/pages/RetrievalPage";
import { ConfoundsPage } from "@/features/c1-procon/pages/ConfoundsPage";
import { MapLookupPage } from "@/features/c1-procon/pages/MapLookupPage";
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
      { path: "retrieval", element: <RetrievalPage /> },
      { path: "confounds", element: <ConfoundsPage /> },
      { path: "map", element: <MapLookupPage /> },
      { path: "evidence", element: <EvidencePage /> },
    ],
  },
];
