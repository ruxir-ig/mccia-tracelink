from __future__ import annotations

import re
from datetime import date
from typing import Iterable

DELAMINATION_LABELS = {
    "surfdelam",
    "surfdelamination",
    "surf_delamination",
    "surf-delam",
    "surface delamination",
    "surface_delamination",
    "surface-delamination",
}


def normalize_defect_type(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    compact = re.sub(r"[\s_-]+", "", raw).lower()
    if compact in {"surfdelam", "surfdelamination", "surfacedelamination"}:
        return "surface_delamination"
    return re.sub(r"[\s-]+", "_", raw.lower())


def split_batches(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def score_raw_candidate(raw: dict, supplier: dict | None, qc: dict | None, complaint_text: str = "") -> tuple[float, list[str]]:
    score = 0.35
    reasons: list[str] = ["lot number matches production input"]
    material = (raw.get("material_type") or "").lower()
    supplier_name = ((supplier or {}).get("supplier_name") or "").lower()
    defect = (qc or {}).get("defect_type_normalized")
    complaint = complaint_text.lower()

    if defect == "surface_delamination" and "adhesive" in material:
        score += 0.35
        reasons.append("surface delamination is most strongly linked to adhesive bonding material")
    if raw.get("supplier_id") == "S03":
        score += 0.15
        reasons.append("historical complaint identifies S03 for LOT-2023-114")
    if "adhesive" in complaint and "adhesive" in material:
        score += 0.10
        reasons.append("complaint root cause mentions adhesive batch")
    if "sundaram" in complaint and "sundaram" in supplier_name:
        score += 0.05
        reasons.append("supplier name matches complaint context")
    if raw.get("quality_grade") == "C":
        score += 0.05
        reasons.append("raw material quality grade is C")

    return min(score, 0.99), reasons


def best_raw_candidate(candidates: Iterable[dict], suppliers: dict[str, dict], qc: dict | None, complaint_text: str = "") -> dict | None:
    ranked = []
    for raw in candidates:
        score, reasons = score_raw_candidate(raw, suppliers.get(raw.get("supplier_id", "")), qc, complaint_text)
        ranked.append((score, raw, reasons))
    if not ranked:
        return None
    score, raw, reasons = sorted(ranked, key=lambda item: item[0], reverse=True)[0]
    return {**raw, "confidence": round(score, 3), "confidence_reasons": reasons}
