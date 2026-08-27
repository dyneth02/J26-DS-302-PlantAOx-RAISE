import { ReactNode } from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import { HelpCircle } from "lucide-react";

// Thin wrapper around @radix-ui/react-tooltip, styled to match chartTheme.ts's
// tooltipContentStyle() look so DOM tooltips and Recharts tooltips read as one system.
export function TooltipProvider({ children }: { children: ReactNode }) {
  return <RadixTooltip.Provider delayDuration={150}>{children}</RadixTooltip.Provider>;
}

export default function Tooltip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side="top"
          sideOffset={6}
          className="panel z-[200] max-w-xs p-3 text-xs leading-relaxed text-ink-dim shadow-card"
        >
          {content}
          <RadixTooltip.Arrow className="fill-surface" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

// Convenience "?" info-icon variant for glossary-style callouts (RNIS, BCS, PARRS, ...).
export function InfoTooltip({ content }: { content: ReactNode }) {
  return (
    <Tooltip content={content}>
      <button type="button" className="text-ink-faint transition-colors hover:text-lime" aria-label="More info">
        <HelpCircle size={13} />
      </button>
    </Tooltip>
  );
}
