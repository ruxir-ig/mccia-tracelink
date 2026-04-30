# Scaling TraceLink to 10 Production Lines

TraceLink scales from the demo to 10 production lines by treating each shop-floor event as an append-only trace record: raw-lot receipt, batch start, batch close, QC result, inventory movement, and dispatch. Each line keeps using the same operator UI, but line, machine, shift, and operator become required dimensions in every entry. The FastAPI service can continue to run locally at the plant with SQLite for a pilot; for 10 lines, the same schema should move to PostgreSQL with indexes on `order_id`, `batch_id`, `input_lot_ref`, `machine_id`, and `production_date`.

Offline operation remains local-first. Each tablet or shop-floor PC stores unsynced entries in IndexedDB, shows a clear sync banner, and retries when connectivity returns. The backend accepts idempotent records so duplicate sync attempts do not create duplicate batches. QR stickers can encode lot and batch text only, so there is no per-unit hardware cost; operators can still type the same value if a camera is unavailable.

For Excel dispatch integration, the dispatch CSV import becomes a scheduled file watcher or manual upload at shift close. No ERP migration is required. The system preserves raw imported rows, normalized rows, and link-confidence explanations so QC and plant heads can audit how paper-era records were connected.

Performance at 10 lines is mainly a data-model problem, not an AI problem. Trace queries should read from precomputed dispatch-batch and production-lot links, not scan CSVs. The AI-assisted part is used for fuzzy cleanup, label normalization, Marathi/English guidance, and confidence explanations; the final trace answer is served from indexed tables, keeping recall queries under 30 seconds even during active production.

Operationally, start with one line for two weeks, compare digital records against paper registers, then roll out line by line. Train operators on three actions only: scan or enter raw lot, select machine/shift, and save batch. Supervisors review unresolved links daily, which steadily improves historical traceability without disrupting production.
