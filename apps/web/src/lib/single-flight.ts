const attempts = new Map<string, Promise<void>>();
export function singleFlight(key: string, run: () => Promise<void>) {
  const existing = attempts.get(key);
  if (existing) return existing;
  const task = Promise.resolve()
    .then(run)
    .finally(() => attempts.delete(key));
  attempts.set(key, task);
  return task;
}
