from pydantic import BaseModel
from typing import Any


class BatchEntry(BaseModel):
    date: str
    shift: str
    machine_id: str
    operator_id: str
    raw_lot: str
    units_produced: int
    qc_notes: str | None = None


class ApiResponse(BaseModel):
    data: dict[str, Any]
