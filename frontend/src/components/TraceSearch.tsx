import { useState } from "react";

type TraceResult = {
  query_ms: number;
  dispatch: Record<string, any>;
  batches: Array<{ batch_id: string; production: Record<string, any>; qc: Record<string, any>; raw_material: Record<string, any> }>;
};

export function TraceSearch() {
  const [orderId, setOrderId] = useState("D-1847");
  const [result, setResult] = useState<TraceResult | null>(null);
  const [error, setError] = useState("");

  async function runTrace() {
    setError("");
    const res = await fetch(`/api/trace/dispatch/${orderId.trim()}`);
    if (!res.ok) {
      setError("Dispatch order not found");
      return;
    }
    setResult(await res.json());
  }

  return (
    <section className="card">
      <h2>Trace Dispatch Order</h2>
      <p className="muted">Demo anchor: D-1847</p>
      <div className="row">
        <input value={orderId} onChange={(e) => setOrderId(e.target.value)} aria-label="Dispatch order" />
        <button onClick={runTrace}>Trace</button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="result">
          <div className="metric">Query time: <strong>{result.query_ms} ms</strong></div>
          <h3>{result.dispatch.order_id} · {result.dispatch.customer_id}</h3>
          {result.batches.map((item) => (
            <div className="trace" key={item.batch_id}>
              <strong>{item.batch_id}</strong>
              <span>Raw lot: {item.production?.input_lot_ref}</span>
              <span>Supplier: {item.raw_material?.supplier?.supplier_name} ({item.raw_material?.supplier_id})</span>
              <span>Machine/shift/operator: {item.production?.machine_id} · {item.production?.shift} · {item.production?.operator_id}</span>
              <span>QC: {item.qc?.pass_fail} · {item.qc?.defect_type_normalized || "none"} · {item.qc?.defect_rate_pct}%</span>
              <small>Confidence {Math.round((item.raw_material?.confidence || 0) * 100)}%: {item.raw_material?.confidence_reasons?.join("; ")}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
