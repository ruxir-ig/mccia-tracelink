# TraceLink

AI-powered batch traceability for Precision Auto Parts. Links raw material lots, production batches, QC results, dispatch orders, and OEM defect complaints — from CSV imports through to shop-floor operator entry.

## Stack

- **API** — Hono on Cloudflare Workers (TypeScript)
- **Database** — Cloudflare D1 (SQLite-compatible)
- **Frontend** — React + Vite (Bun package manager)
- **Offline** — IndexedDB queue for operator batch entries

## Quick Start

```bash
# Worker
cd worker
bun install
npx wrangler d1 migrations apply tracelink-db --local
bun run db:generate               # generate seed SQL from CSVs
npx wrangler d1 execute tracelink-db --local --file=scripts/seed.sql
npx wrangler dev --local --port 8787

# Frontend (separate terminal)
cd frontend
bun install
bun run dev
```

Open the Vite URL and use the three panels: **Trace Dispatch Order**, **Contamination Alert**, and **Operator Batch Entry**.

## API Endpoints

```bash
curl http://localhost:8787/api/health
curl http://localhost:8787/api/trace/dispatch/D-1847
curl http://localhost:8787/api/alerts/lot/LOT-2023-114
curl -X POST http://localhost:8787/api/operator/batches \
  -H "Content-Type: application/json" \
  -d '{"date":"2024-03-18","shift":"A","machine_id":"MC-04","operator_id":"OP-101","raw_lot":"LOT-2023-114","units_produced":120}'
```

## Deploy

```bash
cd worker
npx wrangler d1 create tracelink-db              # → paste database_id into wrangler.toml
npx wrangler d1 migrations apply tracelink-db --remote
npx wrangler d1 execute tracelink-db --remote --file=scripts/seed.sql
npx wrangler deploy

cd ../frontend
bun run build
npx wrangler pages deploy dist
```

## Data

CSV sources live in `worker/data/`. Run `bun run db:generate` to produce `scripts/seed.sql`. See `docs/data-cleaning-assumptions.md` for date normalization, batch ID inference, and defect label normalization rules.

## Demo Anchors

- **D-1847** → BATCH-2023-0500 → LOT-2023-114 → supplier S03 Sundaram Clayton, machine MC-04, shift C, QC FAIL surface_delamination 5.74%
- **LOT-2023-114** alert → dispatches D-1847, D-1921, D-2044, D-2102, D-2367
- Raw lot ambiguity resolved by confidence scoring (adhesive material + delamination = highest weight)

## Scaling

See `docs/scaling-to-10-lines.md`.
