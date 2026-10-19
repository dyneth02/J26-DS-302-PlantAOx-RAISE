import type { ReactNode } from "react";

/** Small read-only table used by the C1 pages (kept inside the C1 feature; nothing shared is modified). */
export function SimpleTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr style={{ color: "var(--color-text-muted)" }}>
            {headers.map((h) => (
              <th key={h} className="whitespace-nowrap border-b px-2 py-2 text-xs font-semibold uppercase tracking-wide" style={{ borderColor: "var(--color-border)" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i}>
              {cells.map((cell, j) => (
                <td key={j} className="border-b px-2 py-2 align-top" style={{ borderColor: "var(--color-border)" }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const fmt = (value: number | null | undefined, digits = 3) => (value === null || value === undefined ? "n/a" : value.toFixed(digits));
export const ci = (lo: number, hi: number, digits = 3) => `[${lo.toFixed(digits)}, ${hi.toFixed(digits)}]`;
