import * as fs from "node:fs";
import * as path from "node:path";
import { parseDate, cleanText, toFloat, toInt, batchNum, inferMissingBatchId } from "../src/pipeline";
import { normalizeDefectType, splitBatches } from "../src/linking";

const DATA_DIR = path.resolve(__dirname, "..", "data");

function readCsv<T extends Record<string, string>>(filepath: string): T[] {
  const content = fs.readFileSync(filepath, "utf-8");
  const lines = content.trim().split("\n");
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]);
  const rows: T[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    const row: Record<string, string> = {};
    for (let j = 0; j < headers.length; j++) {
      row[headers[j]] = values[j] ?? "";
    }
    rows.push(row as T);
  }
  return rows;
}

function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        result.push(current.trim());
        current = "";
      } else {
        current += ch;
      }
    }
  }
  result.push(current.trim());
  return result;
}

function escapeSql(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  const str = String(value).replace(/'/g, "''");
  return `'${str}'`;
}

function generateSeed(): void {
  const sqlLines: string[] = ["-- Auto-generated seed data for TraceLink D1 database\n"];

  // Suppliers
  const suppliers = readCsv<any>(path.join(DATA_DIR, "supplier_master.csv"));
  for (const r of suppliers) {
    if (!r.supplier_id) continue;
    sqlLines.push(`INSERT OR REPLACE INTO suppliers VALUES (${escapeSql(r.supplier_id)}, ${escapeSql(r.supplier_name)}, ${escapeSql(r.material_supplied)}, ${toInt(r.lead_time_days)}, ${escapeSql(r.approved_status)});`);
  }
  sqlLines.push("");

  // Raw materials
  const raw = readCsv<any>(path.join(DATA_DIR, "raw_materials_log.csv"));
  for (const r of raw) {
    const lot = cleanText(r.lot_number);
    sqlLines.push(
      `INSERT INTO raw_materials (receipt_date, supplier_id, material_type, lot_number, quantity_kg, quality_grade, inspector_name, missing_lot_number) VALUES (${escapeSql(parseDate(r.receipt_date))}, ${escapeSql(r.supplier_id)}, ${escapeSql(r.material_type)}, ${escapeSql(lot)}, ${toFloat(r.quantity_kg)}, ${escapeSql(r.quality_grade)}, ${escapeSql(r.inspector_name)}, ${lot ? 0 : 1});`
    );
  }
  sqlLines.push("");

  // Production batches
  const production = readCsv<any>(path.join(DATA_DIR, "production_log.csv"));
  for (let idx = 0; idx < production.length; idx++) {
    const r = production[idx];
    let batchId = cleanText(r.batch_id);
    let inferredFlag = 0;
    let confidence = 1.0;
    let reason = "source batch_id present";

    if (!batchId) {
      const inferred = inferMissingBatchId(production, idx);
      if (inferred) {
        batchId = inferred.batch_id;
        inferredFlag = 1;
        confidence = inferred.confidence;
        reason = inferred.reason;
      } else {
        batchId = null;
        inferredFlag = 0;
        confidence = 0.0;
        reason = "unresolved missing batch_id";
      }
    }

    sqlLines.push(
      `INSERT INTO production_batches (production_date, shift, machine_id, operator_id, batch_id, input_lot_ref, units_produced, cycle_time_min, inferred_batch_id, inference_confidence, inference_reason) VALUES (${escapeSql(parseDate(r.date))}, ${escapeSql(r.shift)}, ${escapeSql(r.machine_id)}, ${escapeSql(r.operator_id)}, ${escapeSql(batchId)}, ${escapeSql(cleanText(r.input_lot_ref))}, ${toInt(r.units_produced)}, ${toFloat(r.cycle_time_min)}, ${inferredFlag}, ${confidence}, ${escapeSql(reason)});`
    );
  }
  sqlLines.push("");

  // QC inspections
  const qc = readCsv<any>(path.join(DATA_DIR, "qc_inspection.csv"));
  for (const r of qc) {
    if (!r.batch_id) continue;
    sqlLines.push(
      `INSERT OR REPLACE INTO qc_inspections VALUES (${escapeSql(r.batch_id)}, ${escapeSql(parseDate(r.inspection_date))}, ${escapeSql(r.inspector_id)}, ${escapeSql(r.pass_fail)}, ${escapeSql(r.defect_type)}, ${escapeSql(normalizeDefectType(r.defect_type))}, ${toFloat(r.defect_rate_pct)}, ${escapeSql(r.rework_flag)});`
    );
  }
  sqlLines.push("");

  // Dispatch orders + dispatch_batches
  const dispatch = readCsv<any>(path.join(DATA_DIR, "dispatch_log.csv"));
  for (const r of dispatch) {
    if (!r.order_id) continue;
    sqlLines.push(
      `INSERT OR REPLACE INTO dispatch_orders VALUES (${escapeSql(r.order_id)}, ${escapeSql(parseDate(r.dispatch_date))}, ${escapeSql(r.customer_id)}, ${escapeSql(r.product_type)}, ${toInt(r.quantity)}, ${escapeSql(r.batch_ref)}, ${escapeSql(r.vehicle_number)});`
    );
    for (const batchId of splitBatches(r.batch_ref)) {
      sqlLines.push(
        `INSERT OR IGNORE INTO dispatch_batches VALUES (${escapeSql(r.order_id)}, ${escapeSql(batchId)});`
      );
    }
  }
  sqlLines.push("");

  // Complaints
  const complaints = readCsv<any>(path.join(DATA_DIR, "defect_complaints.csv"));
  for (const r of complaints) {
    if (!r.complaint_id) continue;
    sqlLines.push(
      `INSERT OR REPLACE INTO complaints VALUES (${escapeSql(r.complaint_id)}, ${escapeSql(r.oem_id)}, ${escapeSql(parseDate(r.complaint_date))}, ${escapeSql(r.affected_order_ids)}, ${escapeSql(r.defect_description)}, ${escapeSql(r.root_cause_identified)}, ${escapeSql(r.resolution)}, ${toFloat(r.financial_impact_inr)});`
    );
  }

  const outPath = path.join(DATA_DIR, "..", "scripts", "seed.sql");
  fs.writeFileSync(outPath, sqlLines.join("\n"), "utf-8");
  console.log(`Seed SQL written: ${outPath}`);
  console.log(`SQL statements: ${sqlLines.length}`);
}

generateSeed();
