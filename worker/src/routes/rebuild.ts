import type { Context } from "hono";
import type { Bindings } from "../index";

export async function rebuild(c: Context<{ Bindings: Bindings }>) {
  return c.json({
    status: "ok",
    note: "Database is managed via D1 migrations and seed scripts.",
    commands: {
      migrate: "npx wrangler d1 migrations apply tracelink-db",
      seed: "npx wrangler d1 execute tracelink-db --file=scripts/seed.sql",
    },
  });
}
