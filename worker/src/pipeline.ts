export function parseDate(value: string | null | undefined): string | null {
  if (!value || !String(value).trim()) return null;
  const text = String(value).trim();

  const formats = [
    { regex: /^(\d{4})-(\d{2})-(\d{2})$/, parser: (m: RegExpMatchArray) => `${m[1]}-${m[2]}-${m[3]}` },
    { regex: /^(\d{2})-(\d{2})-(\d{4})$/, parser: (m: RegExpMatchArray) => `${m[3]}-${m[2]}-${m[1]}` },
    { regex: /^(\d{2})\/(\d{2})\/(\d{4})$/, parser: (m: RegExpMatchArray) => `${m[3]}-${m[2]}-${m[1]}` },
    { regex: /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/, parser: (m: RegExpMatchArray) => {
      const a = parseInt(m[1]), b = parseInt(m[2]);
      if (a > 12 && b <= 12) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
      return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
    }},
  ];

  for (const { regex, parser } of formats) {
    const m = text.match(regex);
    if (m) return parser(m);
  }

  const d = new Date(text);
  if (!isNaN(d.getTime())) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  return text;
}

export function cleanText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text || null;
}

export function toInt(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.floor(n) : null;
}

export function toFloat(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function batchNum(batchId: string): number | null {
  const parts = batchId.split("-");
  const last = parts[parts.length - 1];
  const n = parseInt(last, 10);
  return Number.isFinite(n) ? n : null;
}

export function inferMissingBatchId(
  rows: Array<Record<string, string>>,
  idx: number
): { batch_id: string; confidence: number; reason: string } | null {
  const prevId = nextBatchId(rows, idx, -1);
  const nextId = nextBatchId(rows, idx, 1);
  if (!prevId || !nextId) return null;

  const prevNum = batchNum(prevId);
  const nextNum = batchNum(nextId);
  if (prevNum === null || nextNum === null) return null;

  const gap = nextNum - prevNum;
  if (gap > 1 && gap <= 8) {
    const prefix = prevId.substring(0, prevId.lastIndexOf("-"));
    const newNum = prevNum + 1;
    return {
      batch_id: `${prefix}-${String(newNum).padStart(4, "0")}`,
      confidence: 0.82,
      reason: "inferred from neighboring sequential batch IDs",
    };
  }
  return null;
}

function nextBatchId(rows: Array<Record<string, string>>, idx: number, step: number): string | null {
  let pos = idx + step;
  while (pos >= 0 && pos < rows.length && Math.abs(pos - idx) <= 8) {
    const value = cleanText(rows[pos]?.batch_id);
    if (value) return value;
    pos += step;
  }
  return null;
}
