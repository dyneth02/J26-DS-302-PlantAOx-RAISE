import type { RouteObject } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { C2Nav } from "@/features/c2-pu/components/C2Nav";
import { OverviewPage } from "@/features/c2-pu/pages/OverviewPage";
import { Fr1Page } from "@/features/c2-pu/pages/Fr1Page";
import { Fr2Page } from "@/features/c2-pu/pages/Fr2Page";
import { Fr3Page } from "@/features/c2-pu/pages/Fr3Page";
import { Fr4Page } from "@/features/c2-pu/pages/Fr4Page";
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
      { path: "fr1", element: <Fr1Page /> },
      { path: "fr2", element: <Fr2Page /> },
      { path: "fr3", element: <Fr3Page /> },
      { path: "fr4", element: <Fr4Page /> },
      { path: "curriculum", element: <CurriculumPage /> },
      { path: "evidence", element: <EvidencePage /> },
    ],
  },
];
