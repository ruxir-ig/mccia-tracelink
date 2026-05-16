"""AI Query endpoints for natural language interface — Enhanced NLU."""
from __future__ import annotations

import time
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import get_current_user
from ..db import connect

router = APIRouter(prefix="/ai", tags=["ai"])

class QueryRequest(BaseModel):
    query: str


# ── Intent keyword sets (fuzzy matching) ────────────────────────
_SHIFT_KEYWORDS = {"shift", "shifts", "worst shift", "best shift", "shift intelligence", "shift performance", "shift analysis", "team performance"}
_FAIL_KEYWORDS = {"fail", "failed", "failure", "failures", "reject", "rejected", "rejections", "defective", "bad batches", "qc fail", "quality issue", "quality issues"}
_LOT_KEYWORDS = {"lot", "raw material", "raw lot", "input lot", "material lot", "lot number"}
_MACHINE_KEYWORDS = {"machine", "machines", "equipment", "mc-", "machine performance", "machine stats", "line performance"}
_SUPPLIER_KEYWORDS = {"supplier", "suppliers", "vendor", "vendors", "supplier scorecard", "supplier quality", "supply chain"}
_COMPLAINT_KEYWORDS = {"complaint", "complaints", "oem", "customer issue", "customer complaint", "field failure", "warranty"}
_DISPATCH_KEYWORDS = {"dispatch", "dispatches", "order", "orders", "shipment", "shipments", "delivery", "deliveries"}
_IMPUTE_KEYWORDS = {"missing", "impute", "imputation", "synthetic", "inferred", "imputed", "data gap", "gap analysis"}
_SUMMARY_KEYWORDS = {"summary", "overview", "status", "dashboard", "stats", "statistics", "how are things", "report", "kpi", "metrics"}
_EXPLAIN_KEYWORDS = {"what is", "what are", "explain", "meaning", "definition", "define", "tell me about"}
_GREETING_KEYWORDS = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy"}
_THANKS_KEYWORDS = {"thank", "thanks", "thank you", "appreciate", "great", "awesome", "perfect", "good job", "nice"}
_CSV_KEYWORDS = {"csv", "upload", "import", "file upload", "data import", "how to upload"}
_COUNT_KEYWORDS = {"how many", "count", "total", "number of"}
_QUALITY_KEYWORDS = {"quality", "qc", "inspection", "inspections", "pass rate", "defect rate", "yield"}
_HELP_KEYWORDS = {"help", "what can", "how do", "guide", "tutorial", "commands", "capabilities"}


def _matches_any(q: str, keywords: set[str]) -> bool:
    """Check if the query matches any of the keywords (substring or exact)."""
    for kw in keywords:
        if kw in q:
            return True
    return False


def _extract_lot(q: str) -> str | None:
    """Try to extract a lot number from the query."""
    # LOT-2023-114, LOT2023114, lot 114, etc.
    patterns = [
        r'lot[\s\-]*([\w\-]+)',
        r'(LOT[\-\s]?\d{4}[\-\s]?\d+)',
        r'lot\s+(\d+)',
    ]
    for pat in patterns:
        match = re.search(pat, q, re.IGNORECASE)
        if match:
            lot = match.group(1).upper().strip()
            if not lot.startswith("LOT"):
                lot = "LOT-" + lot
            # Normalize format: LOT-YYYY-NNN
            lot = re.sub(r'^LOT[\s\-]*(\d{4})[\s\-]*(\d+)$', r'LOT-\1-\2', lot)
            return lot
    return None


def _extract_machine(q: str) -> str | None:
    """Try to extract a machine ID from the query."""
    match = re.search(r'mc[\s\-]*(\d+)', q, re.IGNORECASE)
    if match:
        return f"MC-{match.group(1).zfill(2)}"
    return None


def _extract_order(q: str) -> str | None:
    """Try to extract a dispatch order ID from the query."""
    match = re.search(r'd[\s\-]*(\d+)', q, re.IGNORECASE)
    if match:
        return f"D-{match.group(1)}"
    return None


def _extract_shift(q: str) -> str | None:
    """Try to extract a specific shift from the query."""
    match = re.search(r'\bshift\s+([abc])\b', q, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


@router.post("/query")
async def ai_query(req: QueryRequest, user: dict = Depends(get_current_user)):
    start = time.perf_counter()
    conn = connect()
    q = req.query.lower().strip()
    user_id = user.get("user_id")
    
    response = {
        "text": "",
        "data": None,
        "type": "text"
    }

    try:
        # ── Greetings ───────────────────────────────────────────
        if _matches_any(q, _GREETING_KEYWORDS) and len(q) < 30:
            response["text"] = "Hello! I'm your TraceLink AI Assistant. I can help you navigate supply chain data, analyze quality metrics, and investigate traceability issues. What would you like to explore today?"
            response["type"] = "help"

        # ── Thanks / Farewell ──────────────────────────────────
        elif _matches_any(q, _THANKS_KEYWORDS) and len(q) < 50:
            response["text"] = "You're welcome! I'm always here to help. Feel free to ask me anything about your production data, quality metrics, or supply chain traceability."
            response["type"] = "text"

        # ── Count Queries ──────────────────────────────────────
        elif _matches_any(q, _COUNT_KEYWORDS):
            counts = {}
            table_labels = {
                "production_batches": "Production Batches",
                "qc_inspections": "QC Inspections",
                "dispatch_orders": "Dispatch Orders",
                "raw_materials": "Raw Materials",
                "complaints": "Complaints",
                "suppliers": "Suppliers",
            }
            for t, label in table_labels.items():
                counts[label] = conn.execute(f"SELECT COUNT(*) as cnt FROM {t} WHERE user_id = ?", (user_id,)).fetchone()["cnt"]
            
            # Try to match specific table
            target = None
            if "batch" in q or "production" in q: target = "Production Batches"
            elif "qc" in q or "inspection" in q or "quality" in q: target = "QC Inspections"
            elif "dispatch" in q or "order" in q or "shipment" in q: target = "Dispatch Orders"
            elif "material" in q or "raw" in q: target = "Raw Materials"
            elif "complaint" in q or "oem" in q: target = "Complaints"
            elif "supplier" in q or "vendor" in q: target = "Suppliers"
            
            if target:
                response["text"] = f"You currently have **{counts[target]:,}** {target.lower()} in the system."
            else:
                lines = [f"Here's a count of all your records:\n"]
                for label, cnt in counts.items():
                    lines.append(f"• **{label}:** {cnt:,}")
                response["text"] = "\n".join(lines)
            response["type"] = "summary"

        # ── Compound: Failed batches from specific shift ───────
        elif (_matches_any(q, _FAIL_KEYWORDS) and _extract_shift(q)):
            shift = _extract_shift(q)
            rows = conn.execute("""
                SELECT q.batch_id, q.inspection_date, q.pass_fail, q.defect_type_normalized, 
                       q.defect_rate_pct, p.machine_id, p.shift, p.operator_id
                FROM qc_inspections q
                LEFT JOIN production_batches p ON p.batch_id = q.batch_id AND p.user_id = q.user_id
                WHERE q.pass_fail = 'FAIL' AND p.shift = ? AND q.user_id = ?
                ORDER BY q.inspection_date DESC LIMIT 50
            """, (shift, user_id)).fetchall()
            if rows:
                response["text"] = f"Found **{len(rows)}** failed QC inspections from **Shift {shift}**:"
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = f"No failed inspections found for Shift {shift}."

        # ── Shift Intelligence ──────────────────────────────────
        elif _matches_any(q, _SHIFT_KEYWORDS):
            rows = conn.execute("""
                SELECT p.shift, COUNT(*) as total_inspections,
                       SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                       ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                FROM qc_inspections q
                JOIN production_batches p ON p.batch_id = q.batch_id AND p.user_id = q.user_id
                WHERE p.shift IS NOT NULL AND LENGTH(p.shift) <= 5 AND p.user_id = ?
                GROUP BY p.shift
                ORDER BY failures DESC
            """, (user_id,)).fetchall()
            if rows:
                worst = rows[0]
                best = rows[-1]
                response["text"] = (
                    f"Shift intelligence analysis complete:\n\n"
                    f"• **Worst Performing:** Shift {worst['shift']} — {worst['failures']} failures, "
                    f"{worst['avg_defect_rate']}% avg defect rate\n"
                    f"• **Best Performing:** Shift {best['shift']} — {best['failures']} failures, "
                    f"{best['avg_defect_rate']}% avg defect rate\n\n"
                    f"Full breakdown:"
                )
                response["data"] = [dict(r) for r in rows]
                response["type"] = "shift_metrics"
            else:
                response["text"] = "No shift data available yet. Upload production and QC files to enable shift analysis."

        # ── Quality / QC Overview ──────────────────────────────
        elif _matches_any(q, _QUALITY_KEYWORDS) and not _matches_any(q, _FAIL_KEYWORDS):
            total_qc = conn.execute("SELECT COUNT(*) as cnt FROM qc_inspections WHERE user_id = ?", (user_id,)).fetchone()["cnt"]
            pass_qc = conn.execute("SELECT COUNT(*) as cnt FROM qc_inspections WHERE pass_fail = 'PASS' AND user_id = ?", (user_id,)).fetchone()["cnt"]
            fail_qc = total_qc - pass_qc
            pass_rate = round((pass_qc / total_qc * 100) if total_qc > 0 else 0, 1)
            
            response["text"] = (
                f"Quality overview:\n\n"
                f"• **Total Inspections:** {total_qc:,}\n"
                f"• **Passed:** {pass_qc:,}\n"
                f"• **Failed:** {fail_qc:,}\n"
                f"• **Pass Rate:** {pass_rate}%\n\n"
                f"{'⚠️ Pass rate is below 80%. Consider investigating root causes.' if pass_rate < 80 else '✅ Quality metrics look healthy.'}"
            )
            response["type"] = "summary"

        # ── Explanations ────────────────────────────────────────
        elif _matches_any(q, _EXPLAIN_KEYWORDS):
            if "qc" in q or "inspection" in q or "quality control" in q:
                response["text"] = "**QC (Quality Control) inspections** check production batches against quality standards. TraceLink tracks PASS/FAIL results, defect types, and defect rates for each batch."
            elif "lot" in q or "raw material" in q:
                response["text"] = "A **Lot** (Input Lot Reference) is a unique ID assigned to raw materials from a supplier. TraceLink traces how each lot flows through production batches to finished goods."
            elif "shift" in q:
                response["text"] = "A **Shift** is a working period (Shift A: 06–14h, B: 14–22h, C: 22–06h). Tracking shifts helps identify performance patterns across different teams."
            elif "dispatch" in q or "order" in q:
                response["text"] = "**Dispatch Orders** represent finished goods shipped to customers. TraceLink links each dispatch back to its production batches for full traceability."
            elif "complaint" in q or "oem" in q:
                response["text"] = "**OEM Complaints** are customer-reported issues. TraceLink traces complaints back to specific machines, shifts, and suppliers for root cause analysis."
            elif "imputation" in q or "inferred" in q or "synthetic" in q:
                response["text"] = (
                    "**Batch ID Imputation** is TraceLink's 5-tier system for linking records with missing batch IDs:\n\n"
                    "• **Rule 1 (90%):** Same lot + machine within ±7 days\n"
                    "• **Rule 2 (75%):** Same lot within ±14 days\n"
                    "• **Rule 3 (55%):** Same lot within ±30 days\n"
                    "• **Rule 4 (30%):** Nearest temporal neighbor\n"
                    "• **Rule 5 (0%):** Synthetic ID generated (no match)\n\n"
                    "Higher confidence = stronger data linkage."
                )
            elif "capa" in q or "corrective" in q:
                response["text"] = "**CAPA (Corrective and Preventive Actions)** are formal actions taken to address quality issues. CAPAs track the problem, root cause, corrective steps, and verification status."
            elif "user id" in q or "userid" in q:
                response["text"] = "A **User ID** is your unique account identifier. It isolates your data in our multi-tenant system, ensuring your production data stays private."
            elif "tracelink" in q or "trace link" in q:
                response["text"] = "**TraceLink** is a precision manufacturing traceability platform. It connects raw material lots → production batches → QC inspections → dispatch orders → customer complaints for full supply chain visibility."
            else:
                response["text"] = "I can explain: QC, Lots, Shifts, Dispatch, Complaints, Imputation, CAPA, or TraceLink itself. What concept would you like to understand?"
            response["type"] = "explanation"

        # ── CSV/Upload Help ─────────────────────────────────────
        elif _matches_any(q, _CSV_KEYWORDS):
            response["text"] = (
                "To upload data, go to **Data → Import** in the sidebar. Supported CSV types:\n\n"
                "• **raw_materials** — Lot receipts from suppliers\n"
                "• **production** — Batch production logs\n"
                "• **qc** — Quality inspection results\n"
                "• **dispatch** — Customer shipment orders\n"
                "• **supplier** — Supplier master data\n"
                "• **complaints** — OEM complaint records\n\n"
                "Each CSV must include the required columns. The system will validate and report any errors before processing."
            )
            response["type"] = "help"

        # ── Lot Lookup ──────────────────────────────────────────
        elif _matches_any(q, _LOT_KEYWORDS):
            lot = _extract_lot(q)
            if lot:
                rows = conn.execute(
                    "SELECT batch_id, production_date, machine_id, shift, operator_id, units_produced, inference_confidence FROM production_batches WHERE input_lot_ref = ? AND user_id = ?",
                    (lot, user_id)).fetchall()
                if rows:
                    response["text"] = f"Found **{len(rows)}** production batches linked to lot **{lot}**:"
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = f"No batches found for lot **{lot}**. Try the format LOT-2023-114."
            else:
                response["text"] = "I can trace any lot! Just specify the number, e.g., 'show me lot LOT-2023-114'."

        # ── Failed Batches ──────────────────────────────────────
        elif _matches_any(q, _FAIL_KEYWORDS):
            limit = 50
            rows = conn.execute("""
                SELECT q.batch_id, q.inspection_date, q.pass_fail, q.defect_type_normalized, 
                       q.defect_rate_pct, p.machine_id, p.shift, p.operator_id
                FROM qc_inspections q
                LEFT JOIN production_batches p ON p.batch_id = q.batch_id AND p.user_id = q.user_id
                WHERE q.pass_fail = 'FAIL' AND q.user_id = ?
                ORDER BY q.inspection_date DESC LIMIT ?
            """, (user_id, limit)).fetchall()
            if rows:
                response["text"] = f"Here are the **{len(rows)}** most recent failed QC inspections:"
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "✅ No failed QC inspections found. Your quality metrics look clean!"
            
        # ── Imputation / Missing Data ───────────────────────────
        elif _matches_any(q, _IMPUTE_KEYWORDS):
            rows = conn.execute("""
                SELECT batch_id, input_lot_ref, production_date, machine_id, 
                       inference_confidence, inference_reason
                FROM production_batches 
                WHERE inferred_batch_id = 1 AND user_id = ?
                ORDER BY production_date DESC LIMIT 50
            """, (user_id,)).fetchall()
            if rows:
                total = conn.execute("SELECT COUNT(*) as cnt FROM production_batches WHERE inferred_batch_id = 1 AND user_id = ?", (user_id,)).fetchone()["cnt"]
                response["text"] = f"The imputation engine has inferred **{total}** batch records. Showing the 50 most recent:"
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "✅ No missing batch IDs — all records have original data. No imputation was needed."

        # ── Machine Performance ─────────────────────────────────
        elif _matches_any(q, _MACHINE_KEYWORDS):
            machine = _extract_machine(q)
            if machine:
                rows = conn.execute("""
                    SELECT p.machine_id, COUNT(*) as total_batches,
                           SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                           ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                    FROM production_batches p
                    LEFT JOIN qc_inspections q ON q.batch_id = p.batch_id AND q.user_id = p.user_id
                    WHERE p.machine_id = ? AND p.user_id = ?
                    GROUP BY p.machine_id
                """, (machine, user_id)).fetchall()
                if rows:
                    r = rows[0]
                    fail_pct = round(r['failures'] / max(r['total_batches'], 1) * 100, 1)
                    response["text"] = (
                        f"**{r['machine_id']}** Performance:\n\n"
                        f"• Total Batches: {r['total_batches']}\n"
                        f"• Failures: {r['failures']} ({fail_pct}%)\n"
                        f"• Avg Defect Rate: {r['avg_defect_rate']}%"
                    )
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = f"No data found for machine **{machine}**."
            else:
                rows = conn.execute("""
                    SELECT p.machine_id, COUNT(*) as total_batches,
                           SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                           ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                    FROM production_batches p
                    LEFT JOIN qc_inspections q ON q.batch_id = p.batch_id AND q.user_id = p.user_id
                    WHERE p.machine_id IS NOT NULL AND LENGTH(p.machine_id) <= 10 AND p.user_id = ?
                    GROUP BY p.machine_id
                    ORDER BY failures DESC
                """, (user_id,)).fetchall()
                if rows:
                    response["text"] = "Machine performance summary (ranked by failure count):"
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = "No machine data available yet."

        # ── Supplier Info ───────────────────────────────────────
        elif _matches_any(q, _SUPPLIER_KEYWORDS):
            rows = conn.execute("""
                SELECT s.supplier_id, s.supplier_name, s.approved_status,
                       COUNT(DISTINCT r.lot_number) as lots_supplied,
                       COUNT(DISTINCT c.complaint_id) as complaint_count
                FROM suppliers s
                LEFT JOIN raw_materials r ON r.supplier_id = s.supplier_id AND r.user_id = s.user_id
                LEFT JOIN complaints c ON (c.root_cause_identified LIKE '%' || s.supplier_name || '%' OR c.root_cause_identified LIKE '%' || s.supplier_id || '%') AND c.user_id = s.user_id
                WHERE s.user_id = ?
                GROUP BY s.supplier_id
                ORDER BY complaint_count DESC
            """, (user_id,)).fetchall()
            if rows:
                response["text"] = "Supplier scorecard (sorted by complaint count):"
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "No supplier data found. Upload a supplier master file from the Imports screen."

        # ── Complaints ──────────────────────────────────────────
        elif _matches_any(q, _COMPLAINT_KEYWORDS):
            rows = conn.execute("SELECT * FROM complaints WHERE user_id = ? ORDER BY complaint_date DESC", (user_id,)).fetchall()
            if rows:
                total_impact = sum(r["financial_impact_inr"] or 0 for r in rows)
                response["text"] = f"**{len(rows)}** OEM complaints on record. Total financial impact: **₹{total_impact:,.0f}**."
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "✅ No OEM complaints logged."

        # ── Dispatch / Order Lookup ─────────────────────────────
        elif _matches_any(q, _DISPATCH_KEYWORDS):
            order_id = _extract_order(q)
            if order_id:
                row = conn.execute("SELECT * FROM dispatch_orders WHERE order_id = ? AND user_id = ?", (order_id, user_id)).fetchone()
                if row:
                    response["text"] = f"Dispatch **{order_id}**: shipped {row['dispatch_date']} to customer **{row['customer_id']}**."
                    response["data"] = [dict(row)]
                    response["type"] = "table"
                else:
                    response["text"] = f"Order **{order_id}** not found in dispatch logs."
            else:
                rows = conn.execute("SELECT * FROM dispatch_orders WHERE user_id = ? ORDER BY dispatch_date DESC LIMIT 20", (user_id,)).fetchall()
                if rows:
                    response["text"] = f"Most recent **{len(rows)}** dispatch orders:"
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = "No dispatch orders found."

        # ── Summary / Overview ──────────────────────────────────
        elif _matches_any(q, _SUMMARY_KEYWORDS):
            counts = {}
            for t in ["production_batches", "qc_inspections", "dispatch_orders", "raw_materials", "complaints", "suppliers"]:
                counts[t] = conn.execute(f"SELECT COUNT(*) as cnt FROM {t} WHERE user_id = ?", (user_id,)).fetchone()["cnt"]
            total_qc = counts["qc_inspections"]
            pass_qc = conn.execute("SELECT COUNT(*) as cnt FROM qc_inspections WHERE pass_fail = 'PASS' AND user_id = ?", (user_id,)).fetchone()["cnt"]
            pass_rate = round((pass_qc / total_qc * 100) if total_qc > 0 else 0, 1)
            
            response["text"] = (
                f"**TraceLink Environment Summary:**\n\n"
                f"• **Production Batches:** {counts['production_batches']:,}\n"
                f"• **QC Inspections:** {counts['qc_inspections']:,} (pass rate: {pass_rate}%)\n"
                f"• **Dispatch Orders:** {counts['dispatch_orders']:,}\n"
                f"• **Raw Materials:** {counts['raw_materials']:,}\n"
                f"• **Suppliers:** {counts['suppliers']:,}\n"
                f"• **Complaints:** {counts['complaints']:,}\n\n"
                f"Need details on any area? Just ask!"
            )
            response["type"] = "summary"

        # ── Help / Default ──────────────────────────────────────
        elif _matches_any(q, _HELP_KEYWORDS):
            response["text"] = (
                "Here's what I can help with:\n\n"
                "📊 **Analytics:**\n"
                "• *'worst shift'* — Shift performance analysis\n"
                "• *'quality overview'* — QC pass/fail summary\n"
                "• *'machine MC-03 performance'* — Machine-level stats\n\n"
                "🔍 **Traceability:**\n"
                "• *'show lot LOT-2023-114'* — Full lot trace\n"
                "• *'dispatch D-1847'* — Order lookup\n"
                "• *'failed batches from shift A'* — Filtered failures\n\n"
                "📋 **Data:**\n"
                "• *'how many batches'* — Record counts\n"
                "• *'supplier scorecard'* — Supplier quality ranking\n"
                "• *'show complaints'* — OEM complaint log\n"
                "• *'show imputed batches'* — Imputation audit\n\n"
                "ℹ️ **Concepts:**\n"
                "• *'what is imputation'* — Explains TraceLink concepts\n"
                "• *'system overview'* — Full dashboard summary"
            )
            response["type"] = "help"
        
        else:
            response["text"] = (
                "I'm not sure I understood that. Try asking about:\n\n"
                "• Shifts, quality, machines, or failures\n"
                "• Lot tracing or dispatch lookups\n"
                "• Supplier scores or complaint history\n"
                "• *'help'* for a full command list"
            )

    except Exception as e:
        response["text"] = f"Error processing query: {str(e)}"
        
    finally:
        conn.close()

    response["query_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return response
