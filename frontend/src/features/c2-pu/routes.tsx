import type { RouteObject } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { C2Nav } from "@/features/c2-pu/components/C2Nav";
import { OverviewPage } from "@/features/c2-pu/pages/OverviewPage";
import { So1Page } from "@/features/c2-pu/pages/So1Page";
import { So2Page } from "@/features/c2-pu/pages/So2Page";
import { So3Page } from "@/features/c2-pu/pages/So3Page";
import { So4Page } from "@/features/c2-pu/pages/So4Page";
import { CurriculumPage } from "@/features/c2-pu/pages/CurriculumPage";
import { EvidencePage } from "@/features/c2-pu/pages/EvidencePage";

function C2Layout() {
  return (
    <div className="space-y-6">
      <C2Nav />
      <Outlet />
    </div>
  );
}

/**
 * This component's full route contribution. The shared router composition
 * (src/app/router.tsx) only needs to spread this array in -- nothing about
 * C2's internal page structure leaks out.
 */
export const c2PuRoutes: RouteObject[] = [
  {
    path: "c2",
    element: <C2Layout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "so1", element: <So1Page /> },
      { path: "so2", element: <So2Page /> },
      { path: "so3", element: <So3Page /> },
      { path: "so4", element: <So4Page /> },
      { path: "curriculum", element: <CurriculumPage /> },
      { path: "evidence", element: <EvidencePage /> },
    ],
  },
];
