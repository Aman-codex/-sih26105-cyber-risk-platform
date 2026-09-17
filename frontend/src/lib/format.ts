/**
 * Consistent, locale-independent money formatting used across the whole
 * dashboard (Assets, Controls, Risk Overview) so the same number always
 * looks the same everywhere, regardless of the viewer's browser locale.
 */
export function fmtMoney(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}
