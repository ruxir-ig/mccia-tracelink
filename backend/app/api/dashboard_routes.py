"""Dashboard metrics endpoint with TTL cache for performance."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..db import connect

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ── In-memory TTL cache ──────────────────────────────────────────
_dashboard_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 30


def _get_cached(user_id: str) -> dict[str, Any] | None:
    entry = _dashboard_cache.get(user_id)
    if entry and (time.time() - entry["_ts"]) < _CACHE_TTL_SECONDS:
        return entry
    return None


def invalidate_dashboard_cache(user_id: str) -> None:
    """Called after imports to force fresh metrics on next load."""
    _dashboard_cache.pop(user_id, None)


@router.get("/metrics")
async def dashboard_metrics(user: dict = Depends(get_current_user)):
    user_id = user.get("user_id")

    # Check cache first
    cached = _get_cached(user_id)
    if cached:
        result = {k: v for k, v in cached.items() if k != "_ts"}
        result["_cached"] = True
        return result

    conn = connect()
    try:
        # ── Combined batch + QC stats (single pass) ──────────────
        batch_count = conn.execute(
            "SELECT COUNT(DISTINCT batch_id) as cnt FROM production_batches WHERE user_id = ? AND batch_id IS NOT NULL",
            (user_id,),
        ).fetchone()["cnt"]

        qc_row = conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN pass_fail='PASS' THEN 1 ELSE 0 END) as passed FROM qc_inspections WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total_qc = qc_row["total"]
        pass_qc = qc_row["passed"] or 0
        pass_rate = round((pass_qc / total_qc * 100) if total_qc > 0 else 0, 1)

        # Defect trend (last 10 dates)
        defect_trend = [dict(r) for r in conn.execute("""
            SELECT inspection_date, COUNT(*) as total,
                   SUM(CASE WHEN pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                   ROUND(AVG(COALESCE(defect_rate_pct, 0)), 2) as avg_defect_rate
            FROM qc_inspections
            WHERE inspection_date IS NOT NULL 
              AND LENGTH(inspection_date) >= 8
              AND inspection_date NOT LIKE '%script%'
              AND inspection_date NOT LIKE '%DROP%'
              AND user_id = ?
            GROUP BY inspection_date
            HAVING total > 0
            ORDER BY inspection_date DESC
            LIMIT 10
        """, (user_id,)).fetchall()]

        # Top failing machines
        top_machines = [dict(r) for r in conn.execute("""
            SELECT p.machine_id, COUNT(*) as fail_count,
                   ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
            FROM qc_inspections q
            JOIN production_batches p ON p.batch_id = q.batch_id AND p.user_id = q.user_id
            WHERE q.pass_fail = 'FAIL' AND p.machine_id IS NOT NULL AND q.user_id = ?
            GROUP BY p.machine_id
            ORDER BY fail_count DESC
            LIMIT 5
        """, (user_id,)).fetchall()]

        # Shift Intelligence
        shift_metrics = [dict(r) for r in conn.execute("""
            SELECT p.shift, COUNT(*) as total_inspections,
                   SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as fail_count,
                   ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
            FROM qc_inspections q
            JOIN production_batches p ON p.batch_id = q.batch_id AND p.user_id = q.user_id
            WHERE p.shift IS NOT NULL AND q.user_id = ?
            GROUP BY p.shift
            ORDER BY fail_count DESC
        """, (user_id,)).fetchall()]

        # Supplier scorecard
        supplier_scorecard = [dict(r) for r in conn.execute("""
            SELECT s.supplier_id, s.supplier_name, s.approved_status,
                   COUNT(DISTINCT r.lot_number) as lots_supplied,
                   COUNT(DISTINCT c.complaint_id) as complaint_count
            FROM suppliers s
            LEFT JOIN raw_materials r ON r.supplier_id = s.supplier_id AND r.user_id = s.user_id
            LEFT JOIN complaints c ON (c.root_cause_identified LIKE '%' || s.supplier_name || '%' OR c.root_cause_identified LIKE '%' || s.supplier_id || '%') AND c.user_id = s.user_id
            WHERE s.user_id = ?
            GROUP BY s.supplier_id
            ORDER BY complaint_count DESC
        """, (user_id,)).fetchall()]

        # Counts (combined into fewer queries)
        counts = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM complaints WHERE user_id = ?) as open_complaints,
                (SELECT COALESCE(SUM(COALESCE(financial_impact_inr, 0)), 0) FROM complaints WHERE user_id = ?) as financial_exposure,
                (SELECT COUNT(*) FROM operator_entries WHERE supervisor_approved = 0 AND user_id = ?) as pending_entries,
                (SELECT COUNT(*) FROM corrective_actions WHERE status = 'open' AND user_id = ?) as open_cas
        """, (user_id, user_id, user_id, user_id)).fetchone()

        # Unresolved links
        unresolved = conn.execute("""
            SELECT COUNT(*) as cnt 
            FROM production_batches p
            LEFT JOIN trace_reviews tr ON tr.batch_id = p.batch_id AND tr.lot_number = p.input_lot_ref AND tr.user_id = p.user_id
            WHERE p.inferred_batch_id = 1 AND p.user_id = ? AND tr.status IS NULL
        """, (user_id,)).fetchone()["cnt"]

        # Recent complaints
        recent_complaints = [dict(r) for r in conn.execute("""
            SELECT complaint_id, oem_id, complaint_date, defect_description, root_cause_identified, financial_impact_inr
            FROM complaints
            WHERE user_id = ?
            ORDER BY complaint_date DESC, complaint_id DESC
            LIMIT 25
        """, (user_id,)).fetchall()]

        # Recent imports
        recent_imports = [dict(r) for r in conn.execute(
            "SELECT import_id, filename, file_type, status, row_count, uploaded_at FROM source_files WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 5", (user_id,)
        ).fetchall()]

        result = {
            "batch_count": batch_count,
            "pass_rate": pass_rate,
            "defect_trend": defect_trend,
            "top_failing_machines": top_machines,
            "supplier_scorecard": supplier_scorecard,
            "open_complaints": counts["open_complaints"],
            "financial_exposure": counts["financial_exposure"],
            "recent_complaints": recent_complaints,
            "pending_operator_entries": counts["pending_entries"],
            "unresolved_links": unresolved,
            "recent_imports": recent_imports,
            "open_corrective_actions": counts["open_cas"],
            "shift_metrics": shift_metrics,
        }

        # Cache it
        _dashboard_cache[user_id] = {**result, "_ts": time.time()}

        return result
    finally:
        conn.close()
