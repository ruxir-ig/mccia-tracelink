from fastapi.testclient import TestClient

from app.linking import normalize_defect_type, split_batches
from app.main import app
from app.pipeline import rebuild_database


def client():
    rebuild_database()
    return TestClient(app)


def test_defect_normalization_variants():
    assert normalize_defect_type("surf-delam") == "surface_delamination"
    assert normalize_defect_type("SurfDeLam") == "surface_delamination"
    assert normalize_defect_type("surface delamination") == "surface_delamination"
    assert split_batches("BATCH-1,BATCH-2") == ["BATCH-1", "BATCH-2"]


def test_trace_d_1847_full_chain():
    res = client().get("/api/trace/dispatch/D-1847")
    assert res.status_code == 200
    data = res.json()
    batch = data["batches"][0]
    assert data["dispatch"]["customer_id"] == "OEM-TATA"
    assert batch["batch_id"] == "BATCH-2023-0500"
    assert batch["production"]["input_lot_ref"] == "LOT-2023-114"
    assert batch["production"]["machine_id"] == "MC-04"
    assert batch["production"]["shift"] == "C"
    assert batch["qc"]["pass_fail"] == "FAIL"
    assert batch["qc"]["defect_type_normalized"] == "surface_delamination"
    assert batch["qc"]["defect_rate_pct"] == 5.74
    assert batch["raw_material"]["supplier_id"] == "S03"
    assert batch["raw_material"]["supplier"]["supplier_name"] == "Sundaram Clayton"
    assert data["query_ms"] < 30000


def test_lot_2023_114_alert_contains_anchor_orders():
    res = client().get("/api/alerts/lot/LOT-2023-114")
    assert res.status_code == 200
    data = res.json()
    orders = {row["order_id"] for row in data["affected_dispatch_orders"]}
    assert {"D-1847", "D-1921", "D-2044", "D-2102", "D-2367"}.issubset(orders)
    assert data["summary"]["dispatch_order_count"] >= 5
    assert data["query_ms"] < 30000


def test_operator_entry_endpoint():
    res = client().post("/api/operator/batches", json={
        "date": "2024-03-18",
        "shift": "A",
        "machine_id": "MC-04",
        "operator_id": "OP-101",
        "raw_lot": "LOT-2023-114",
        "units_produced": 120,
        "qc_notes": "visual check ok"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "saved"
