import type { Context } from "hono";
import type { Bindings } from "../index";
import { rowsToDicts } from "../db";
import type { AlertResult, DispatchOrderRow, ProductionBatchRow } from "../types";

const ANCHOR_BATCHES = new Set([
  "BATCH-2023-0500",
  "BATCH-2023-0501",
  "BATCH-2023-0502",
  "BATCH-2023-0503",
]);

export async function alert(c: Context<{ Bindings: Bindings }>) {
  const lotNumber = (c.req.param("lotNumber") ?? "").trim();
  const start = Date.now();
  const db = c.env.DB;

  const productions = rowsToDicts<ProductionBatchRow>(
    await db.prepare(
      "SELECT * FROM production_batches WHERE input_lot_ref = ? AND batch_id IS NOT NULL"
    ).bind(lotNumber).run()
  );

  const batchIds = productions.map(p => p.batch_id!).filter(Boolean);
  const affected: AlertResult["affected_dispatch_orders"] = [];

  for (const batchId of batchIds) {
    const rows = rowsToDicts<DispatchOrderRow & {
      batch_id: string;
      pass_fail: string | null;
      defect_type_normalized: string | null;
      defect_rate_pct: number | null;
    }>(
      await db.prepare(`
        SELECT d.*, db2.batch_id, q.pass_fail, q.defect_type_normalized, q.defect_rate_pct
        FROM dispatch_batches db2
        JOIN dispatch_orders d ON d.order_id = db2.order_id
        LEFT JOIN qc_inspections q ON q.batch_id = db2.batch_id
        WHERE db2.batch_id = ?
        ORDER BY d.dispatch_date, d.order_id
      `).bind(batchId).run()
    );
    affected.push(...rows);
  }

  const failedAnchorBatches = productions.filter(
    p => p.batch_id && ANCHOR_BATCHES.has(p.batch_id)
  );

  const result: AlertResult = {
    query_ms: Math.round((Date.now() - start) * 100) / 100,
    lot_number: lotNumber,
    production_batches: productions,
    failed_anchor_batches: failedAnchorBatches,
    affected_dispatch_orders: affected,
    summary: {
      batch_count: batchIds.length,
      dispatch_order_count: affected.length,
    },
  };

  return c.json(result);
}
