interface BadgeProps {
  children: React.ReactNode;
  className?: string;
  /** Agent-specific color override */
  color?: string;
}

export function Badge({ children, className = "", color }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center gap-1
        rounded-full px-2.5 py-0.5
        text-xs font-semibold
        ${color ?? "bg-zinc-700 text-zinc-200"}
        ${className}
      `}
    >
      {children}
    </span>
  );
}
