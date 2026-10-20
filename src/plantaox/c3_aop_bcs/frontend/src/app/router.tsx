import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { c3AopBcsRoutes } from "@/features/c3-aop-bcs/routes";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: c3AopBcsRoutes,
  },
]);
