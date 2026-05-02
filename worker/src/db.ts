export function rowToDict<T>(row: Record<string, unknown> | null | undefined): T | null {
  if (!row) return null;
  return { ...row } as unknown as T;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function rowsToDicts<T>(result: any): T[] {
  return (result.results ?? []) as unknown as T[];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function singleRowDict<T>(result: any): T | null {
  return rowToDict<T>(result.results?.[0] ?? null);
}
