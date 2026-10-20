import type { RouteObject } from "react-router-dom";
import { C3Shell } from "@/features/c3-aop-bcs/components/C3Shell";
import { OverviewPage } from "@/features/c3-aop-bcs/pages/OverviewPage";
import { DatasetPage } from "@/features/c3-aop-bcs/pages/DatasetPage";
import { PerturbationsPage } from "@/features/c3-aop-bcs/pages/PerturbationsPage";
import { MetricsPage } from "@/features/c3-aop-bcs/pages/MetricsPage";
import { ExplorerPage } from "@/features/c3-aop-bcs/pages/ExplorerPage";
import { PredictorsPage } from "@/features/c3-aop-bcs/pages/PredictorsPage";
import { EvidencePage } from "@/features/c3-aop-bcs/pages/EvidencePage";
import "@/features/c3-aop-bcs/c3-aop-bcs.css";

export const c3AopBcsRoutes: RouteObject[] = [{
  path: "c3",
  element: <C3Shell />,
  children: [
    { index: true, element: <OverviewPage /> },
    { path: "dataset", element: <DatasetPage /> },
    { path: "perturbations", element: <PerturbationsPage /> },
    { path: "metrics", element: <MetricsPage /> },
    { path: "explorer", element: <ExplorerPage /> },
    { path: "predictors", element: <PredictorsPage /> },
    { path: "evidence", element: <EvidencePage /> },
  ],
}];
