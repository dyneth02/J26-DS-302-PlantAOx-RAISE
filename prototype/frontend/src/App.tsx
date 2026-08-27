import { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import { TooltipProvider } from "./components/Tooltip";
import Home from "./pages/Home";

// Route-level code splitting: each component page pulls in its own chart/animation
// weight, so only the page the user actually navigates to is fetched -- Home (the
// landing page, first thing loaded) stays eager.
const C1Page = lazy(() => import("./pages/C1Page"));
const C2Page = lazy(() => import("./pages/C2Page"));
const C3Page = lazy(() => import("./pages/C3Page"));
const C4Page = lazy(() => import("./pages/C4Page"));

function RouteFallback() {
  return (
    <div className="flex h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-lime/30 border-t-lime" />
    </div>
  );
}

export default function App() {
  return (
    <TooltipProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route
            path="/c1"
            element={
              <Suspense fallback={<RouteFallback />}>
                <C1Page />
              </Suspense>
            }
          />
          <Route
            path="/c2"
            element={
              <Suspense fallback={<RouteFallback />}>
                <C2Page />
              </Suspense>
            }
          />
          <Route
            path="/c3"
            element={
              <Suspense fallback={<RouteFallback />}>
                <C3Page />
              </Suspense>
            }
          />
          <Route
            path="/c4"
            element={
              <Suspense fallback={<RouteFallback />}>
                <C4Page />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </TooltipProvider>
  );
}
