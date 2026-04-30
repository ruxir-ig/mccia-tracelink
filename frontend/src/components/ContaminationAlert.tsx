import { useState } from "react";

type AlertResult = {
  query_ms: number;
  lot_number: string;
  summary: { batch_count: number; dispatch_order_count: number };
  affected_dispatch_orders: Record<string, any>[];
};

export function ContaminationAlert() {
  const [lot, setLot] = useState("LOT-2023-114");
  const [result, setResult] = useState<AlertResult | null>(null);

  async function runAlert() {
    const res = await fetch(`/api/alerts/lot/${lot.trim()}`);
    setResult(await res.json());
  }

  return (
    <section className="card">
      <h2>Contamination Alert</h2>
      <p className="muted">Find every dispatch order touched by a suspect lot.</p>
      <div className="row">
        <input value={lot} onChange={(e) => setLot(e.target.value)} aria-label="Lot number" />
        <button onClick={runAlert}>Simulate Alert</button>
      </div>
      {result && (
        <div className="result">
          <div className="metric">{result.summary.dispatch_order_count} orders at risk · {result.query_ms} ms</div>
          <div className="table">
            <div className="thead"><span>Order</span><span>OEM</span><span>Date</span><span>Batch</span><span>QC</span></div>
            {result.affected_dispatch_orders.map((row) => (
              <div className="trow" key={`${row.order_id}-${row.batch_id}`}>
                <span>{row.order_id}</span><span>{row.customer_id}</span><span>{row.dispatch_date}</span><span>{row.batch_id}</span><span>{row.pass_fail || "-"} {row.defect_rate_pct ? `${row.defect_rate_pct}%` : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
