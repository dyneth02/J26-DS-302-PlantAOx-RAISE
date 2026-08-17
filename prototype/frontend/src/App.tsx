import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import C1Page from "./pages/C1Page";
import C2Page from "./pages/C2Page";
import C3Page from "./pages/C3Page";
import C4Page from "./pages/C4Page";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/c1" element={<C1Page />} />
        <Route path="/c2" element={<C2Page />} />
        <Route path="/c3" element={<C3Page />} />
        <Route path="/c4" element={<C4Page />} />
      </Route>
    </Routes>
  );
}
