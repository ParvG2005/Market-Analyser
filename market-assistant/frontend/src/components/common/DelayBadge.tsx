interface DelayBadgeProps {
  delayed: boolean;
  delayMinutes: number;
}

/** Small inline flag for delayed feeds (e.g. equities at 15-min delay). */
export function DelayBadge({ delayed, delayMinutes }: DelayBadgeProps) {
  if (!delayed) return null;
  return <span className="delay-badge badge badge-neutral">{delayMinutes}-min delayed</span>;
}
