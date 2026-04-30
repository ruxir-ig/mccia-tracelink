# Data Cleaning Assumptions

TraceLink ingests the six CSV files at the repository root and rebuilds `backend/tracelink.sqlite3`. The rebuild is deterministic so a judge can rerun the same files and get the same trace output.

## Date Normalization

`raw_materials_log.csv` contains mixed date formats. The loader first tries ISO, Indian day-first, slash day-first, and US slash formats, then falls back to `python-dateutil`. All stored dates are ISO `YYYY-MM-DD`.

## Batch and Dispatch Linking

Dispatch `batch_ref` can contain comma-separated batches. The pipeline splits this into a `dispatch_batches` join table so contamination alerts catch every order that contains any affected batch. Production rows with missing `batch_id` are kept in the database and marked as unresolved unless the neighboring source rows make a short sequential gap obvious. Inferred IDs carry `inferred_batch_id`, `inference_confidence`, and `inference_reason`.

## QC Defect Labels

Known surface-delamination variants such as `surf-delam`, `SurfDeLam`, `surf_delamination`, `surface delamination`, and `surface_delamination` are normalized to `surface_delamination`. Raw values are still retained for audit.

## Ambiguous Raw Lots

The raw-material log can reuse the same lot number across suppliers and materials. TraceLink therefore ranks raw-material candidates instead of joining only on `lot_number`. For a delamination failure, adhesive bonding material is weighted highest; complaint text, supplier `S03`, quality grade, and supplier-master context add confidence. This resolves D-1847 to `LOT-2023-114` from supplier `S03` / Sundaram Clayton while showing the reasons.

## Demo Ground Truth

`D-1847` links to `BATCH-2023-0500`, machine `MC-04`, shift `C`, operator `OP-001`, QC `FAIL`, defect rate `5.74%`, and normalized defect `surface_delamination`. `LOT-2023-114` contamination alerts include the failed anchor batches `BATCH-2023-0500` through `BATCH-2023-0503` and their downstream dispatch orders.
