import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export function Button({ className = "", variant = "default", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "ghost" }) {
  const v = {
    default: "border hairline bg-surface hover:bg-ground",
    primary: "bg-indigo text-plaster hover:opacity-90 dark:text-ink",
    danger: "bg-alarm text-plaster hover:opacity-90",
    ghost: "hover:bg-surface",
  }[variant];
  return <button type="button" {...props} className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-sm disabled:opacity-50 ${v} ${className}`} />;
}

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`rounded border hairline bg-surface ${className}`} />;
}

export function Label({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`font-mono text-[11px] uppercase tracking-widest text-fg-muted ${className}`}>{children}</span>;
}

export function SeverityBar({ severity }: { severity: "low" | "medium" | "high" | null }) {
  const cls = { high: "border-alarm", medium: "border-sandstone", low: "border-indigo" }[severity ?? "low"];
  return <span aria-hidden className={`absolute inset-y-0 left-0 w-1 border-l-3 ${severity ? cls : "border-line"}`} />;
}
