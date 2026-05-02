import type { Context } from "hono";
import type { Bindings } from "../index";

export async function health(c: Context<{ Bindings: Bindings }>) {
  return c.json({ ok: true, database: "tracelink-db" });
}
