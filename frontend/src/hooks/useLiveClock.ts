import { useEffect, useState } from 'react';

export function useLiveClock(pollIntervalMs: number = 15000) {
  const [now, setNow] = useState<Date>(new Date());
  const [secondsUntilPoll, setSecondsUntilPoll] = useState<number>(Math.floor(pollIntervalMs / 1000));

  useEffect(() => {
    const timer = setInterval(() => {
      const current = new Date();
      setNow(current);

      const elapsedInCycle = Math.floor((current.getTime() % pollIntervalMs) / 1000);
      const remaining = Math.max(1, Math.floor(pollIntervalMs / 1000) - elapsedInCycle);
      setSecondsUntilPoll(remaining);
    }, 1000);

    return () => clearInterval(timer);
  }, [pollIntervalMs]);

  // Format UTC: YYYY-MM-DD HH:mm:ss UTC
  const utcString = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';

  return {
    now,
    utcString,
    secondsUntilPoll,
  };
}
