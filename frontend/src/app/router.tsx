import { createBrowserRouter, Outlet } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { PlatformOverviewPage } from "@/app/pages/PlatformOverviewPage";
import { NotIntegratedPage } from "@/app/pages/NotIntegratedPage";
import { c2PuRoutes } from "@/features/c2-pu/routes";
import { c4ScreenRoutes } from "@/features/c4-screen/routes";

function RootLayout() {
  return (
    <AppShell title="PlantAOx-RAISE">
      <Outlet />
    </AppShell>
  );
}

/**
 * Shared composition root. A new component registers here with ONE line:
 * `...c3AopBcsRoutes` spread into `children`, exactly like `c2PuRoutes`
 * below -- nothing else in this file is component-specific.
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <PlatformOverviewPage /> },
      { path: "not-integrated/:componentId", element: <NotIntegratedPage /> },
      ...c2PuRoutes,
      ...c4ScreenRoutes,
    ],
  },
]);
