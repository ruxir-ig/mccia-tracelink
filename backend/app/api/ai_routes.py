"""AI Query endpoints for natural language interface."""
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

@router.post("/query")
async def ai_query(req: QueryRequest, user: dict = Depends(get_current_user)):
    start = time.perf_counter()
    conn = connect()
    q = req.query.lower().strip()
    
    response = {
        "text": "",
        "data": None,
        "type": "text"
    }

    try:
        # ── Shift Intelligence ──────────────────────────────────
        if "worst shift" in q or ("shift" in q and ("fail" in q or "performance" in q or "best" in q or "intelligence" in q)):
            rows = conn.execute("""
                SELECT p.shift, COUNT(*) as total_inspections,
                       SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                       ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                FROM qc_inspections q
                JOIN production_batches p ON p.batch_id = q.batch_id
                WHERE p.shift IS NOT NULL
                GROUP BY p.shift
                ORDER BY failures DESC
            """).fetchall()
            if rows:
                worst = rows[0]
                best = rows[-1]
                response["text"] = (
                    f"Shift Intelligence Summary:\n"
                    f"• Worst: Shift {worst['shift']} — {worst['failures']} failures, "
                    f"avg defect rate {worst['avg_defect_rate']}%\n"
                    f"• Best: Shift {best['shift']} — {best['failures']} failures, "
                    f"avg defect rate {best['avg_defect_rate']}%"
                )
                response["data"] = [dict(r) for r in rows]
                response["type"] = "shift_metrics"
            else:
                response["text"] = "No shift data available yet. Upload production and QC files first."

        # ── Lot Lookup ──────────────────────────────────────────
        elif "lot" in q:
            match = re.search(r'lot[\s\-]*([a-zA-Z0-9\-]+)', q)
            if match:
                lot = match.group(1).upper()
                if not lot.startswith("LOT-"):
                    lot = "LOT-" + lot
                rows = conn.execute("SELECT batch_id, production_date, machine_id, shift, operator_id, units_produced, inference_confidence FROM production_batches WHERE input_lot_ref = ?", (lot,)).fetchall()
                if rows:
                    response["text"] = f"Found {len(rows)} production batches linked to {lot}."
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = f"No batches found for lot '{lot}'. Check the lot number format (e.g., LOT-2023-114)."
            else:
                response["text"] = "Please specify a lot number, e.g., 'show me lot LOT-2023-114'."

        # ── Failed Batches ──────────────────────────────────────
        elif "fail" in q or "failed" in q or "reject" in q:
            limit = 50
            rows = conn.execute("""
                SELECT q.batch_id, q.inspection_date, q.pass_fail, q.defect_type_normalized, 
                       q.defect_rate_pct, p.machine_id, p.shift, p.operator_id
                FROM qc_inspections q
                LEFT JOIN production_batches p ON p.batch_id = q.batch_id
                WHERE q.pass_fail = 'FAIL' 
                ORDER BY q.inspection_date DESC LIMIT ?
            """, (limit,)).fetchall()
            if rows:
                response["text"] = f"Found {len(rows)} recently failed QC inspections."
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "No failed QC inspections found in the database."
            
        # ── Imputation / Missing Data ───────────────────────────
        elif "missing" in q or "impute" in q or "imputation" in q or "synthetic" in q or "inferred" in q:
            rows = conn.execute("""
                SELECT batch_id, input_lot_ref, production_date, machine_id, 
                       inference_confidence, inference_reason
                FROM production_batches 
                WHERE inferred_batch_id = 1 
                ORDER BY production_date DESC LIMIT 50
            """).fetchall()
            if rows:
                total = conn.execute("SELECT COUNT(*) as cnt FROM production_batches WHERE inferred_batch_id = 1").fetchone()["cnt"]
                response["text"] = f"Found {total} imputed batch IDs total. Showing the most recent 50."
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "No imputed batch IDs found. All batch IDs were present in the uploaded data."

        # ── Machine Performance ─────────────────────────────────
        elif "machine" in q:
            match = re.search(r'(mc[\s\-]*\d+)', q)
            if match:
                machine = match.group(1).upper().replace(" ", "-")
                if not "-" in machine[2:]:
                    machine = "MC-" + machine[2:]
                rows = conn.execute("""
                    SELECT p.machine_id, COUNT(*) as total_batches,
                           SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                           ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                    FROM production_batches p
                    LEFT JOIN qc_inspections q ON q.batch_id = p.batch_id
                    WHERE p.machine_id = ?
                    GROUP BY p.machine_id
                """, (machine,)).fetchall()
                if rows:
                    r = rows[0]
                    response["text"] = f"Machine {r['machine_id']}: {r['total_batches']} batches, {r['failures']} failures, avg defect rate {r['avg_defect_rate']}%."
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = f"No data found for machine '{machine}'."
            else:
                rows = conn.execute("""
                    SELECT p.machine_id, COUNT(*) as total_batches,
                           SUM(CASE WHEN q.pass_fail = 'FAIL' THEN 1 ELSE 0 END) as failures,
                           ROUND(AVG(q.defect_rate_pct), 2) as avg_defect_rate
                    FROM production_batches p
                    LEFT JOIN qc_inspections q ON q.batch_id = p.batch_id
                    WHERE p.machine_id IS NOT NULL
                    GROUP BY p.machine_id
                    ORDER BY failures DESC
                """).fetchall()
                if rows:
                    response["text"] = "Machine performance summary (ordered by failure count):"
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = "No machine data available yet."

        # ── Supplier Info ───────────────────────────────────────
        elif "supplier" in q:
            rows = conn.execute("""
                SELECT s.supplier_id, s.supplier_name, s.approved_status,
                       COUNT(DISTINCT r.lot_number) as lots_supplied,
                       COUNT(DISTINCT c.complaint_id) as complaint_count
                FROM suppliers s
                LEFT JOIN raw_materials r ON r.supplier_id = s.supplier_id
                LEFT JOIN complaints c ON c.root_cause_identified LIKE '%' || s.supplier_name || '%'
                GROUP BY s.supplier_id
                ORDER BY complaint_count DESC
            """).fetchall()
            if rows:
                response["text"] = "Supplier scorecard:"
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "No supplier data available. Upload supplier master file first."

        # ── Complaints ──────────────────────────────────────────
        elif "complaint" in q or "oem" in q:
            rows = conn.execute("SELECT * FROM complaints ORDER BY complaint_date DESC").fetchall()
            if rows:
                total_impact = sum(r["financial_impact_inr"] or 0 for r in rows)
                response["text"] = f"Found {len(rows)} complaints. Total financial impact: ₹{total_impact:,.0f}."
                response["data"] = [dict(r) for r in rows]
                response["type"] = "table"
            else:
                response["text"] = "No complaints in the system."

        # ── Dispatch / Order Lookup ─────────────────────────────
        elif "dispatch" in q or "order" in q:
            match = re.search(r'd[\s\-]*(\d+)', q)
            if match:
                order_id = "D-" + match.group(1)
                row = conn.execute("SELECT * FROM dispatch_orders WHERE order_id = ?", (order_id,)).fetchone()
                if row:
                    response["text"] = f"Order {order_id}: dispatched {row['dispatch_date']} to {row['customer_id']}."
                    response["data"] = [dict(row)]
                    response["type"] = "table"
                else:
                    response["text"] = f"Order '{order_id}' not found."
            else:
                rows = conn.execute("SELECT * FROM dispatch_orders ORDER BY dispatch_date DESC LIMIT 20").fetchall()
                if rows:
                    response["text"] = f"Showing the 20 most recent dispatch orders."
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = "No dispatch orders found."

        # ── Summary / Overview ──────────────────────────────────
        elif "summary" in q or "overview" in q or "status" in q or "dashboard" in q or "stats" in q:
            counts = {}
            for t in ["production_batches", "qc_inspections", "dispatch_orders", "raw_materials", "complaints", "suppliers"]:
                counts[t] = conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()["cnt"]
            total_qc = counts["qc_inspections"]
            pass_qc = conn.execute("SELECT COUNT(*) as cnt FROM qc_inspections WHERE pass_fail = 'PASS'").fetchone()["cnt"]
            pass_rate = round((pass_qc / total_qc * 100) if total_qc > 0 else 0, 1)
            
            response["text"] = (
                f"System Overview:\n"
                f"• Production batches: {counts['production_batches']}\n"
                f"• QC inspections: {counts['qc_inspections']} (pass rate: {pass_rate}%)\n"
                f"• Dispatch orders: {counts['dispatch_orders']}\n"
                f"• Raw materials: {counts['raw_materials']}\n"
                f"• Suppliers: {counts['suppliers']}\n"
                f"• Complaints: {counts['complaints']}"
            )
            response["type"] = "summary"

        # ── Help / Default ──────────────────────────────────────
        elif "help" in q or "what can" in q or "how" in q:
            response["text"] = (
                "I can answer questions about your TraceLink data. Try:\n"
                "• 'What is the worst shift?' — Shift performance analysis\n"
                "• 'Show me lot LOT-2023-114' — Lot traceability\n"
                "• 'Show failed batches' — Recent QC failures\n"
                "• 'Machine MC-03 performance' — Machine analytics\n"
                "• 'Supplier scorecard' — Supplier quality metrics\n"
                "• 'Show complaints' — OEM complaint history\n"
                "• 'System overview' — Dashboard summary\n"
                "• 'Show imputed batches' — Imputation audit\n"
                "• 'Show dispatch D-1847' — Order lookup"
            )
            response["type"] = "help"
        
        else:
            response["text"] = (
                "I couldn't understand that query. Try asking about:\n"
                "• Shift performance (e.g., 'worst shift')\n"
                "• Lot tracing (e.g., 'lot LOT-2023-114')\n"
                "• Failed batches, machine stats, suppliers, complaints\n"
                "• System overview or type 'help' for all commands"
            )

    except Exception as e:
        response["text"] = f"Error processing query: {str(e)}"
        
    finally:
        conn.close()

    response["query_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return response
