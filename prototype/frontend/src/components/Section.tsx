import { ReactNode } from "react";
import { useSectionRegistry } from "../hooks/useSectionRegistry";

export default function Section({
  id,
  label,
  notes,
  children,
}: {
  id: string;
  label: string;
  notes?: string;
  children: ReactNode;
}) {
  useSectionRegistry(id, label, notes);
  return (
    <div data-section-id={id} className="scroll-mt-24">
      {children}
    </div>
  );
}
