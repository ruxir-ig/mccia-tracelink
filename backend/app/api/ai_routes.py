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
    q = req.query.lower()
    
    response = {
        "text": "I could not understand your query. Try asking about 'failed batches', 'worst shift', or 'lot <number>'.",
        "data": None,
        "type": "text"
    }

    try:
        if "worst shift" in q or "shift" in q:
            # Shift Intelligence
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
                response["text"] = f"The worst performing shift is Shift {worst['shift']} with {worst['failures']} failed batches and an average defect rate of {worst['avg_defect_rate']}%."
                response["data"] = [dict(r) for r in rows]
                response["type"] = "shift_metrics"

        elif "lot" in q:
            # Try to extract lot number
            match = re.search(r'lot\s+([a-zA-Z0-9\-]+)', q)
            if match:
                lot = match.group(1).upper()
                rows = conn.execute("SELECT * FROM production_batches WHERE input_lot_ref = ?", (lot,)).fetchall()
                if rows:
                    response["text"] = f"I found {len(rows)} production batches associated with Lot {lot}."
                    response["data"] = [dict(r) for r in rows]
                    response["type"] = "table"
                else:
                    response["text"] = f"I couldn't find any batches associated with Lot {lot}."
            else:
                response["text"] = "Please specify a lot number, e.g., 'show me lot LOT-123'."

        elif "fail" in q or "failed" in q:
            limit = 50
            rows = conn.execute("SELECT * FROM qc_inspections WHERE pass_fail = 'FAIL' ORDER BY inspection_date DESC LIMIT ?", (limit,)).fetchall()
            response["text"] = f"Here are the most recent failed QC inspections."
            response["data"] = [dict(r) for r in rows]
            response["type"] = "table"
            
        elif "missing" in q or "impute" in q or "imputation" in q:
            rows = conn.execute("SELECT * FROM production_batches WHERE inferred_batch_id = 1 ORDER BY production_date DESC LIMIT 50").fetchall()
            response["text"] = f"Here are the most recently imputed production batches."
            response["data"] = [dict(r) for r in rows]
            response["type"] = "table"

    except Exception as e:
        response["text"] = f"Error processing query: {str(e)}"
        
    finally:
        conn.close()

    response["query_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return response
