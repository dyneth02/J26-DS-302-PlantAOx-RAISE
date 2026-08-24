import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Scenario {
  id: string;
  label: string;
  page: string; // e.g. "c4"
  state: Record<string, unknown>;
  savedAt: number;
}

interface ScenarioState {
  scenarios: Scenario[];
  save: (page: string, label: string, state: Record<string, unknown>) => void;
  remove: (id: string) => void;
}

// Needs to survive both a route change (Layout unmounts the outgoing page on every nav)
// and a page reload -- persist middleware handles the latter, the store itself (living
// outside any page component) handles the former.
export const useScenarioStore = create<ScenarioState>()(
  persist(
    (set) => ({
      scenarios: [],
      save: (page, label, state) =>
        set((s) => ({
          scenarios: [
            ...s.scenarios,
            { id: `${page}-${Date.now()}`, label, page, state, savedAt: Date.now() },
          ].slice(-10), // keep the most recent 10 across all pages
        })),
      remove: (id) => set((s) => ({ scenarios: s.scenarios.filter((x) => x.id !== id) })),
    }),
    { name: "plantaox-scenarios" }
  )
);
