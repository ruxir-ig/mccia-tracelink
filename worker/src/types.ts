export interface SupplierRow {
  supplier_id: string;
  supplier_name: string;
  material_supplied: string;
  lead_time_days: number;
  approved_status: string;
}

export interface RawMaterialRow {
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

export interface ProductionBatchRow {
  production_id: number;
  production_date: string | null;
  shift: string;
  machine_id: string;
  operator_id: string;
  batch_id: string | null;
  input_lot_ref: string | null;
  units_produced: number | null;
  cycle_time_min: number | null;
  inferred_batch_id: number;
  inference_confidence: number;
  inference_reason: string | null;
}

export interface QcInspectionRow {
  batch_id: string;
  inspection_date: string | null;
  inspector_id: string;
  pass_fail: string;
  defect_type_raw: string | null;
  defect_type_normalized: string | null;
  defect_rate_pct: number | null;
  rework_flag: string | null;
}

export interface DispatchOrderRow {
  order_id: string;
  dispatch_date: string | null;
  customer_id: string;
  product_type: string;
  quantity: number | null;
  batch_ref: string | null;
  vehicle_number: string | null;
}

export interface ComplaintRow {
  complaint_id: string;
  oem_id: string;
  complaint_date: string | null;
  affected_order_ids: string | null;
  defect_description: string | null;
  root_cause_identified: string | null;
  resolution: string | null;
  financial_impact_inr: number | null;
}

export interface RawResolved {
  raw_id: number;
  receipt_date: string | null;
  supplier_id: string;
  material_type: string;
  lot_number: string;
  quantity_kg: number | null;
  quality_grade: string;
  inspector_name: string;
  missing_lot_number: number;
  supplier: Omit<SupplierRow, "supplier_id"> & { supplier_id: string } | null;
  confidence: number;
  confidence_reasons: string[];
}

export interface TraceBatchItem {
  batch_id: string;
  production: ProductionBatchRow | null;
  qc: QcInspectionRow | null;
  raw_material: RawResolved | null;
}

export interface TraceResult {
  query_ms: number;
  dispatch: DispatchOrderRow | null;
  batches: TraceBatchItem[];
}

export interface AlertResult {
  query_ms: number;
  lot_number: string;
  production_batches: ProductionBatchRow[];
  failed_anchor_batches: ProductionBatchRow[];
  affected_dispatch_orders: Array<DispatchOrderRow & {
    batch_id: string;
    pass_fail: string | null;
    defect_type_normalized: string | null;
    defect_rate_pct: number | null;
  }>;
  summary: { batch_count: number; dispatch_order_count: number };
}

export interface BatchEntry {
  date: string;
  shift: string;
  machine_id: string;
  operator_id: string;
  raw_lot: string;
  units_produced: number;
  qc_notes?: string;
}

export interface CsvSupplierRow {
  supplier_id: string;
  supplier_name: string;
  material_supplied: string;
  lead_time_days: string;
  approved_status: string;
}

export interface CsvRawMaterialRow {
  receipt_date: string;
  supplier_id: string;
  material_type: string;
  lot_number: string;
  quantity_kg: string;
  quality_grade: string;
  inspector_name: string;
}

export interface CsvProductionRow {
  date: string;
  shift: string;
  machine_id: string;
  operator_id: string;
  batch_id: string;
  input_lot_ref: string;
  units_produced: string;
  cycle_time_min: string;
}

export interface CsvQcRow {
  batch_id: string;
  inspection_date: string;
  inspector_id: string;
  pass_fail: string;
  defect_type: string;
  defect_rate_pct: string;
  rework_flag: string;
}

export interface CsvDispatchRow {
  dispatch_date: string;
  order_id: string;
  customer_id: string;
  product_type: string;
  quantity: string;
  batch_ref: string;
  vehicle_number: string;
}

export interface CsvComplaintRow {
  complaint_id: string;
  oem_id: string;
  complaint_date: string;
  affected_order_ids: string;
  defect_description: string;
  root_cause_identified: string;
  resolution: string;
  financial_impact_inr: string;
}
