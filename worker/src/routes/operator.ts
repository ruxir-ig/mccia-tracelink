import type { Context } from "hono";
import type { Bindings } from "../index";
import type { BatchEntry } from "../types";

export async function operator(c: Context<{ Bindings: Bindings }>) {
  const body = await c.req.json<BatchEntry>();
  const db = c.env.DB;

  if (!body.raw_lot || !body.machine_id || !body.operator_id || !body.units_produced) {
    return c.json({ error: "Missing required fields: raw_lot, machine_id, operator_id, units_produced" }, 400);
  }

  const result = await db.prepare(
    `INSERT INTO operator_entries
     (production_date, shift, machine_id, operator_id, raw_lot, units_produced, qc_notes)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    body.date,
    body.shift,
    body.machine_id,
    body.operator_id,
    body.raw_lot,
    body.units_produced,
    body.qc_notes ?? null
  ).run();

  return c.json({ status: "saved", entry_id: result.meta.last_row_id });
}
