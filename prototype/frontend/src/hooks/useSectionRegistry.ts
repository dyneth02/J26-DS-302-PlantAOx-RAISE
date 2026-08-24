import { useEffect } from "react";
import { usePresentationStore } from "../store/presentationStore";

// Registers a page section with the global presentation toolbar so prev/next can
// scroll to it. Registration/unregistration rides on the existing route-change
// unmount (Layout's AnimatePresence already tears down the outgoing page on every
// nav, which fires this hook's cleanup) -- no extra route-change listener needed.
export function useSectionRegistry(id: string, label: string, notes?: string) {
  const register = usePresentationStore((s) => s.register);
  const unregister = usePresentationStore((s) => s.unregister);

  useEffect(() => {
    register({ id, label, notes });
    return () => unregister(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, label, notes]);
}
