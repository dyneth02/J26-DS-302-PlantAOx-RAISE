import { create } from "zustand";

interface SectionEntry {
  id: string;
  label: string;
  notes?: string;
}

interface PresentationState {
  sections: SectionEntry[];
  currentIndex: number;
  fullscreen: boolean;
  autoplay: boolean;
  safeMode: boolean;
  presenterNotes: boolean;
  resetSignal: number;
  register: (entry: SectionEntry) => void;
  unregister: (id: string) => void;
  clearSections: () => void;
  goTo: (index: number) => void;
  next: () => void;
  prev: () => void;
  toggleFullscreen: () => void;
  toggleAutoplay: () => void;
  toggleSafeMode: () => void;
  togglePresenterNotes: () => void;
  reset: () => void;
}

// Lives outside any single page's component tree because Layout's toolbar and the
// routed page are siblings via <Outlet/>, and because Layout's AnimatePresence
// mode="wait" unmounts the outgoing page on every navigation -- page-local state
// can't survive either of those, so this is the one place a shared store earns its
// keep over plain useState.
export const usePresentationStore = create<PresentationState>((set, get) => ({
  sections: [],
  currentIndex: 0,
  fullscreen: false,
  autoplay: false,
  safeMode: localStorage.getItem("plantaox-safe-mode") === "1",
  presenterNotes: localStorage.getItem("plantaox-presenter-notes") === "1",
  resetSignal: 0,

  register: (entry) =>
    set((s) => (s.sections.some((x) => x.id === entry.id) ? s : { sections: [...s.sections, entry] })),

  unregister: (id) => set((s) => ({ sections: s.sections.filter((x) => x.id !== id) })),

  clearSections: () => set({ sections: [], currentIndex: 0 }),

  goTo: (index) => {
    const { sections } = get();
    if (index < 0 || index >= sections.length) return;
    set({ currentIndex: index });
    document
      .querySelector(`[data-section-id="${sections[index].id}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  },

  next: () => get().goTo(get().currentIndex + 1),
  prev: () => get().goTo(get().currentIndex - 1),

  toggleFullscreen: () => {
    const next = !get().fullscreen;
    if (next) document.documentElement.requestFullscreen?.().catch(() => {});
    else if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    set({ fullscreen: next });
  },

  toggleAutoplay: () => set((s) => ({ autoplay: !s.autoplay })),

  toggleSafeMode: () =>
    set((s) => {
      const next = !s.safeMode;
      localStorage.setItem("plantaox-safe-mode", next ? "1" : "0");
      return { safeMode: next };
    }),

  togglePresenterNotes: () =>
    set((s) => {
      const next = !s.presenterNotes;
      localStorage.setItem("plantaox-presenter-notes", next ? "1" : "0");
      return { presenterNotes: next };
    }),

  reset: () => set((s) => ({ resetSignal: s.resetSignal + 1, currentIndex: 0 })),
}));
