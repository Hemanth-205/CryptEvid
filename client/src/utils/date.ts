/**
 * Safe date formatting helpers that will never throw RangeError: Invalid time value
 * or cause React components to crash into a blank screen.
 */

export function formatIsoDateSafe(dateVal: any, length: number = 16): string {
  if (!dateVal) return '--';
  try {
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return String(dateVal);
    const iso = d.toISOString();
    return iso.replace('T', ' ').substring(0, length);
  } catch {
    return String(dateVal || '--');
  }
}

export function formatLocalDateSafe(dateVal: any): string {
  if (!dateVal) return '--';
  try {
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return String(dateVal);
    return d.toLocaleString();
  } catch {
    return String(dateVal || '--');
  }
}
