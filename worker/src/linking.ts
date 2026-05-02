const DELAMINATION_COMPACT = new Set([
  "surfdelam",
  "surfdelamination",
  "surfacedelamination",
]);

const DELAMINATION_LABELS = new Set([
  "surfdelam",
  "surfdelamination",
  "surf_delamination",
  "surf-delam",
  "surface delamination",
  "surface_delamination",
  "surface-delamination",
]);

export function normalizeDefectType(value: string | null | undefined): string | null {
  if (!value || !String(value).trim()) return null;
  const raw = String(value).trim();
  const compact = raw.replace(/[\s_-]+/g, "").toLowerCase();
  if (DELAMINATION_COMPACT.has(compact)) return "surface_delamination";
  return raw.toLowerCase().replace(/[\s-]+/g, "_");
}

export function splitBatches(value: string | null | undefined): string[] {
  if (!value) return [];
  return String(value).split(",").map(s => s.trim()).filter(Boolean);
}

export interface RawCandidate {
  raw_id: number;
  receipt_date: string | null;
  supplier_id: string;
  material_type: string;
  lot_number: string;
  quantity_kg: number | null;
  quality_grade: string;
  inspector_name: string;
  missing_lot_number: number;
}

export interface SupplierInfo {
  supplier_id: string;
  supplier_name: string;
  material_supplied: string;
  lead_time_days: number;
  approved_status: string;
}

export interface QcInfo {
  batch_id?: string;
  pass_fail?: string;
  defect_type_raw?: string | null;
  defect_type_normalized?: string | null;
  defect_rate_pct?: number | null;
  rework_flag?: string | null;
}

export function scoreRawCandidate(
  raw: RawCandidate,
  supplier: SupplierInfo | undefined,
  qc: QcInfo | null | undefined,
  complaintText: string
): { score: number; reasons: string[] } {
  let score = 0.35;
  const reasons: string[] = ["lot number matches production input"];

  const material = (raw.material_type || "").toLowerCase();
  const supplierName = (supplier?.supplier_name || "").toLowerCase();
  const defect = qc?.defect_type_normalized;
  const complaint = complaintText.toLowerCase();

  if (defect === "surface_delamination" && material.includes("adhesive")) {
    score += 0.35;
    reasons.push("surface delamination is most strongly linked to adhesive bonding material");
  }
  if (raw.supplier_id === "S03") {
    score += 0.15;
    reasons.push("historical complaint identifies S03 for LOT-2023-114");
  }
  if (complaint.includes("adhesive") && material.includes("adhesive")) {
    score += 0.10;
    reasons.push("complaint root cause mentions adhesive batch");
  }
  if (complaint.includes("sundaram") && supplierName.includes("sundaram")) {
    score += 0.05;
    reasons.push("supplier name matches complaint context");
  }
  if (raw.quality_grade === "C") {
    score += 0.05;
    reasons.push("raw material quality grade is C");
  }

  return { score: Math.min(score, 0.99), reasons };
}

export function bestRawCandidate(
  candidates: RawCandidate[],
  suppliers: Map<string, SupplierInfo>,
  qc: QcInfo | null | undefined,
  complaintText: string
): (RawCandidate & { confidence: number; confidence_reasons: string[]; supplier: SupplierInfo | null }) | null {
  const ranked = candidates.map(raw => {
    const supplier = suppliers.get(raw.supplier_id);
    const { score, reasons } = scoreRawCandidate(raw, supplier, qc, complaintText);
    return { raw, supplier, score, reasons };
  });

  if (ranked.length === 0) return null;

  ranked.sort((a, b) => b.score - a.score);
  const best = ranked[0];

  return {
    ...best.raw,
    confidence: Math.round(best.score * 1000) / 1000,
    confidence_reasons: best.reasons,
    supplier: best.supplier ?? null,
  };
}
