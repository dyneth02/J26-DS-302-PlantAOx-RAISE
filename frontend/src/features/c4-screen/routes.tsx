import type { RouteObject } from "react-router-dom";
import { C4Shell } from "@/features/c4-screen/components/C4Shell";
import { OverviewPage } from "@/features/c4-screen/pages/OverviewPage";
import { PipelinePage } from "@/features/c4-screen/pages/PipelinePage";
import { ADExplorerPage } from "@/features/c4-screen/pages/ADExplorerPage";
import { CandidateExplorerPage } from "@/features/c4-screen/pages/CandidateExplorerPage";
import { EvidenceCardsPage } from "@/features/c4-screen/pages/EvidenceCardsPage";
import { AbstainedPage } from "@/features/c4-screen/pages/AbstainedPage";
import { AboutPage } from "@/features/c4-screen/pages/AboutPage";
import "@/features/c4-screen/c4-screen.css";

export const c4ScreenRoutes: RouteObject[] = [
  {
    path: "c4",
    element: <C4Shell />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "pipeline", element: <PipelinePage /> },
      { path: "ad", element: <ADExplorerPage /> },
      { path: "candidates", element: <CandidateExplorerPage /> },
      { path: "cards", element: <EvidenceCardsPage /> },
      { path: "abstained", element: <AbstainedPage /> },
      { path: "about", element: <AboutPage /> },
    ],
  },
];
