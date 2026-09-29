import { useState, useEffect } from 'react';

export function escapeHtml(unsafe: string): string {
  if (!unsafe) return '';
  return unsafe
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function formatTimeAgo(isoString: string | undefined): string {
  if (!isoString) return 'Unknown';
  try {
    const time = new Date(isoString).getTime();
    if (isNaN(time)) return 'Invalid Date';
    
    const diffMs = Date.now() - time;
    const minutes = Math.floor(diffMs / (60 * 1000));
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return 'Invalid Date';
  }
}

export function safeFormatTimestamp(isoString: string | undefined): string {
  if (!isoString) return 'Unknown Time';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'Invalid Time';
    return date.toISOString().replace('T', ' ').substring(11, 19) + ' UTC';
  } catch {
    return 'Unknown Time';
  }
}
