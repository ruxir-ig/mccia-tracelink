import { Hono } from "hono";
import { cors } from "hono/cors";
import type { D1Database } from "@cloudflare/workers-types";
import { health } from "./routes/health";
import { rebuild } from "./routes/rebuild";
import { trace } from "./routes/trace";
import { alert } from "./routes/alert";
import { operator } from "./routes/operator";

export type Bindings = {
  DB: D1Database;
};

const app = new Hono<{ Bindings: Bindings }>();

app.use("*", cors({
  origin: "*",
  allowMethods: ["GET", "POST", "OPTIONS"],
  allowHeaders: ["Content-Type"],
}));

app.get("/api/health", health);
app.post("/api/rebuild", rebuild);
app.get("/api/trace/dispatch/:orderId", trace);
app.get("/api/alerts/lot/:lotNumber", alert);
app.post("/api/operator/batches", operator);

app.notFound((c) => c.json({ error: "not found" }, 404));

app.onError((err, c) => {
  console.error(err);
  return c.json({ error: "internal server error" }, 500);
});

export default app;
