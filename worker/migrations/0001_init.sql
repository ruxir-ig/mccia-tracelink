CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT,
    material_supplied TEXT,
    lead_time_days INTEGER,
    approved_status TEXT
);

CREATE TABLE IF NOT EXISTS raw_materials (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_date TEXT,
    supplier_id TEXT,
    material_type TEXT,
    lot_number TEXT,
    quantity_kg REAL,
    quality_grade TEXT,
    inspector_name TEXT,
    missing_lot_number INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS production_batches (
    production_id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_date TEXT,
    shift TEXT,
    machine_id TEXT,
    operator_id TEXT,
    batch_id TEXT,
    input_lot_ref TEXT,
    units_produced INTEGER,
    cycle_time_min REAL,
    inferred_batch_id INTEGER DEFAULT 0,
    inference_confidence REAL DEFAULT 1.0,
    inference_reason TEXT
);

CREATE TABLE IF NOT EXISTS qc_inspections (
    batch_id TEXT PRIMARY KEY,
    inspection_date TEXT,
    inspector_id TEXT,
    pass_fail TEXT,
    defect_type_raw TEXT,
    defect_type_normalized TEXT,
    defect_rate_pct REAL,
    rework_flag TEXT
);

CREATE TABLE IF NOT EXISTS dispatch_orders (
    order_id TEXT PRIMARY KEY,
    dispatch_date TEXT,
    customer_id TEXT,
    product_type TEXT,
    quantity INTEGER,
    batch_ref TEXT,
    vehicle_number TEXT
);

CREATE TABLE IF NOT EXISTS dispatch_batches (
    order_id TEXT,
    batch_id TEXT,
    PRIMARY KEY (order_id, batch_id)
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id TEXT PRIMARY KEY,
    oem_id TEXT,
    complaint_date TEXT,
    affected_order_ids TEXT,
    defect_description TEXT,
    root_cause_identified TEXT,
    resolution TEXT,
    financial_impact_inr REAL
);

CREATE TABLE IF NOT EXISTS operator_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    production_date TEXT,
    shift TEXT,
    machine_id TEXT,
    operator_id TEXT,
    raw_lot TEXT,
    units_produced INTEGER,
    qc_notes TEXT,
    sync_source TEXT DEFAULT 'web'
);

CREATE INDEX IF NOT EXISTS idx_raw_lot ON raw_materials(lot_number);
CREATE INDEX IF NOT EXISTS idx_prod_batch ON production_batches(batch_id);
CREATE INDEX IF NOT EXISTS idx_prod_lot ON production_batches(input_lot_ref);
CREATE INDEX IF NOT EXISTS idx_dispatch_batch_batch ON dispatch_batches(batch_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_date ON dispatch_orders(dispatch_date);
