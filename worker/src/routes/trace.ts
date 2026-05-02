import type { Context } from "hono";
import type { Bindings } from "../index";
import { singleRowDict, rowsToDicts } from "../db";
import { bestRawCandidate, type SupplierInfo } from "../linking";
import type { DispatchOrderRow, ProductionBatchRow, QcInspectionRow, RawMaterialRow, TraceResult } from "../types";

export async function trace(c: Context<{ Bindings: Bindings }>) {
  const orderId = (c.req.param("orderId") ?? "").trim();
  const start = Date.now();
  const db = c.env.DB;

  const dispatch = singleRowDict<DispatchOrderRow>(
    await db.prepare("SELECT * FROM dispatch_orders WHERE order_id = ?").bind(orderId).run()
  );

  if (!dispatch) {
    return c.json({ error: `Dispatch order ${orderId} not found` }, 404);
  }

  const batchLinks = rowsToDicts<{ batch_id: string }>(
    await db.prepare("SELECT batch_id FROM dispatch_batches WHERE order_id = ? ORDER BY batch_id").bind(orderId).run()
  );

  const suppliers = new Map<string, SupplierInfo>();
  const supplierRows = rowsToDicts<SupplierInfo>(
    await db.prepare("SELECT * FROM suppliers").run()
  );
  for (const s of supplierRows) {
    suppliers.set(s.supplier_id, s);
  }

  const batches: TraceResult["batches"] = [];

  for (const link of batchLinks) {
    const batchId = link.batch_id;

    const production = singleRowDict<ProductionBatchRow>(
      await db.prepare("SELECT * FROM production_batches WHERE batch_id = ? ORDER BY inferred_batch_id LIMIT 1")
        .bind(batchId).run()
    );

    const qc = singleRowDict<QcInspectionRow>(
      await db.prepare("SELECT * FROM qc_inspections WHERE batch_id = ?").bind(batchId).run()
    );

    let rawMaterial = null;
    if (production?.input_lot_ref) {
      const lotRef = production.input_lot_ref;

      const complaintRows = rowsToDicts<{ defect_description: string | null; root_cause_identified: string | null }>(
        await db.prepare("SELECT defect_description, root_cause_identified FROM complaints WHERE root_cause_identified LIKE ?")
          .bind(`%${lotRef}%`).run()
      );
      const complaintText = complaintRows
        .map(r => [r.defect_description ?? "", r.root_cause_identified ?? ""].join(" "))
        .join(" ");

      const candidates = rowsToDicts<RawMaterialRow>(
        await db.prepare("SELECT * FROM raw_materials WHERE lot_number = ?").bind(lotRef).run()
      );

      rawMaterial = bestRawCandidate(candidates, suppliers, qc, complaintText);
    }

    batches.push({
      batch_id: batchId,
      production,
      qc,
      raw_material: rawMaterial,
    });
  }

  const result: TraceResult = {
    query_ms: Math.round((Date.now() - start) * 100) / 100,
    dispatch,
    batches,
  };

  return c.json(result);
}
