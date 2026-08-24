import { useEffect } from "react";
import { motion } from "framer-motion";
import { useHotkeys } from "react-hotkeys-hook";
import { ChevronLeft, ChevronRight, Maximize, Minimize, Play, Pause, RotateCcw, ShieldAlert, StickyNote } from "lucide-react";
import { usePresentationStore } from "../store/presentationStore";

const AUTOPLAY_INTERVAL_MS = 6000;

// Fixed bottom bar, mounted once in Layout.tsx -- the top-right corner is already
// occupied by ThemeToggle, so this lives at the bottom instead.
export default function PresentationToolbar() {
  const sections = usePresentationStore((s) => s.sections);
  const currentIndex = usePresentationStore((s) => s.currentIndex);
  const fullscreen = usePresentationStore((s) => s.fullscreen);
  const autoplay = usePresentationStore((s) => s.autoplay);
  const safeMode = usePresentationStore((s) => s.safeMode);
  const presenterNotes = usePresentationStore((s) => s.presenterNotes);
  const next = usePresentationStore((s) => s.next);
  const prev = usePresentationStore((s) => s.prev);
  const toggleFullscreen = usePresentationStore((s) => s.toggleFullscreen);
  const toggleAutoplay = usePresentationStore((s) => s.toggleAutoplay);
  const toggleSafeMode = usePresentationStore((s) => s.toggleSafeMode);
  const togglePresenterNotes = usePresentationStore((s) => s.togglePresenterNotes);
  const reset = usePresentationStore((s) => s.reset);

  useHotkeys("right", () => next(), [next]);
  useHotkeys("left", () => prev(), [prev]);
  useHotkeys("f", () => !safeMode && toggleFullscreen(), [safeMode, toggleFullscreen]);
  useHotkeys("r", () => reset(), [reset]);
  useHotkeys("space", (e) => {
    e.preventDefault();
    if (!safeMode) toggleAutoplay();
  }, [safeMode, toggleAutoplay]);

  // Safe mode is the live-demo insurance policy: disable autoplay and drop out of
  // fullscreen if it gets turned on mid-presentation, so a flaky venue network/backend
  // can't leave the demo stuck on an animated loop or trapped in fullscreen.
  useEffect(() => {
    if (!safeMode) return;
    if (autoplay) toggleAutoplay();
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
  }, [safeMode]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!autoplay || sections.length === 0) return;
    const id = setInterval(() => {
      const { currentIndex: i, sections: s, goTo } = usePresentationStore.getState();
      goTo((i + 1) % s.length);
    }, AUTOPLAY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoplay, sections.length]);

  if (sections.length === 0) return null;

  const currentNotes = sections[currentIndex]?.notes;

  return (
    <div className="fixed bottom-6 left-[calc(50%+9rem)] z-50 -translate-x-1/2">
      {presenterNotes && (
        <motion.div
          key={sections[currentIndex]?.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mb-2 w-80 rounded-xl border border-amber/30 bg-surface3 p-3 text-xs leading-relaxed text-ink-dim shadow-2xl"
        >
          <p className="label-tag mb-1 text-amber">Presenter notes · {sections[currentIndex]?.label}</p>
          {currentNotes ?? "No notes for this section."}
        </motion.div>
      )}
      <div className="flex items-center gap-1 rounded-2xl border border-line-strong bg-surface3 px-2 py-2 shadow-2xl backdrop-blur-md">
        <button
          onClick={prev}
          disabled={currentIndex <= 0}
          aria-label="Previous section"
          className="rounded-lg p-2 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink disabled:opacity-30"
        >
          <ChevronLeft size={15} />
        </button>

        <span className="label-tag min-w-[7.5rem] truncate px-1 text-center text-ink-dim" title={sections[currentIndex]?.label}>
          {sections[currentIndex]?.label ?? "—"} · {currentIndex + 1}/{sections.length}
        </span>

        <button
          onClick={next}
          disabled={currentIndex >= sections.length - 1}
          aria-label="Next section"
          className="rounded-lg p-2 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink disabled:opacity-30"
        >
          <ChevronRight size={15} />
        </button>

        <div className="mx-1 h-5 w-px bg-line" />

        <button
          onClick={toggleAutoplay}
          disabled={safeMode}
          aria-label={autoplay ? "Pause autoplay" : "Start autoplay"}
          className={`rounded-lg p-2 transition-colors hover:bg-surface2 disabled:opacity-30 ${autoplay ? "text-lime" : "text-ink-faint hover:text-ink"}`}
        >
          {autoplay ? <Pause size={15} /> : <Play size={15} />}
        </button>

        <button
          onClick={toggleFullscreen}
          disabled={safeMode}
          aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          className="rounded-lg p-2 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink disabled:opacity-30"
        >
          {fullscreen ? <Minimize size={15} /> : <Maximize size={15} />}
        </button>

        <button
          onClick={reset}
          aria-label="Reset presentation"
          className="rounded-lg p-2 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink"
        >
          <RotateCcw size={15} />
        </button>

        <div className="mx-1 h-5 w-px bg-line" />

        <button
          onClick={toggleSafeMode}
          aria-label="Toggle safe mode"
          title="Safe mode: hides live-network demo controls, falls back to static data"
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors ${
            safeMode ? "bg-amber/10 text-amber" : "text-ink-faint hover:bg-surface2 hover:text-ink"
          }`}
        >
          <ShieldAlert size={14} />
          Safe mode
        </button>

        <button
          onClick={togglePresenterNotes}
          aria-label="Toggle presenter notes"
          title="Show speaking cues for the current section"
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors ${
            presenterNotes ? "bg-teal/10 text-teal" : "text-ink-faint hover:bg-surface2 hover:text-ink"
          }`}
        >
          <StickyNote size={14} />
          Notes
        </button>
      </div>
    </div>
  );
}
