import { FormEvent, useEffect, useState } from "react";
import { enqueueEntry, getQueuedEntries, syncQueuedEntries } from "../offlineQueue";

const labels = {
  en: { title: "Operator Batch Entry", lot: "Raw lot", machine: "Machine", shift: "Shift", operator: "Operator", units: "Units produced", notes: "QC notes", save: "Save batch" },
  mr: { title: "ऑपरेटर बॅच नोंद", lot: "कच्चा लॉट", machine: "मशीन", shift: "शिफ्ट", operator: "ऑपरेटर", units: "तयार नग", notes: "QC नोंद", save: "बॅच सेव करा" }
};

export function OperatorEntry({ online }: { online: boolean }) {
  const [lang, setLang] = useState<"en" | "mr">("en");
  const [queued, setQueued] = useState(0);
  const [message, setMessage] = useState("");
  const t = labels[lang];

  useEffect(() => {
    getQueuedEntries().then((entries) => setQueued(entries.length));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const entry = {
      date: String(data.get("date")),
      raw_lot: String(data.get("raw_lot")),
      machine_id: String(data.get("machine_id")),
      shift: String(data.get("shift")),
      operator_id: String(data.get("operator_id")),
      units_produced: Number(data.get("units_produced")),
      qc_notes: String(data.get("qc_notes") || "")
    };
    if (!entry.raw_lot || !entry.machine_id || !entry.operator_id || !entry.units_produced) {
      setMessage(lang === "en" ? "Please fill lot, machine, operator, and units." : "लॉट, मशीन, ऑपरेटर आणि नग भरा.");
      return;
    }
    if (!online) {
      await enqueueEntry(entry);
      setQueued((count) => count + 1);
      setMessage(lang === "en" ? "Saved offline. Will sync later." : "ऑफलाइन सेव झाले. नंतर सिंक होईल.");
      event.currentTarget.reset();
      return;
    }
    const res = await fetch("/api/operator/batches", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(entry) });
    setMessage(res.ok ? (lang === "en" ? "Batch saved." : "बॅच सेव झाली.") : "Save failed");
    event.currentTarget.reset();
  }

  async function syncNow() {
    const count = await syncQueuedEntries();
    setQueued(0);
    setMessage(`${count} queued entries synced.`);
  }

  return (
    <section className="card wide">
      <div className="cardHeader">
        <div><h2>{t.title}</h2><p className="muted">Large controls, simple language, offline-first.</p></div>
        <div className="row small"><button onClick={() => setLang("en")}>English</button><button onClick={() => setLang("mr")}>मराठी</button></div>
      </div>
      <form className="operator" onSubmit={submit}>
        <label>Date<input name="date" type="date" required /></label>
        <label>{t.lot}<input name="raw_lot" placeholder="LOT-2023-114" required /></label>
        <label>{t.machine}<select name="machine_id"><option>MC-01</option><option>MC-02</option><option>MC-03</option><option>MC-04</option><option>MC-05</option></select></label>
        <label>{t.shift}<select name="shift"><option>A</option><option>B</option><option>C</option></select></label>
        <label>{t.operator}<input name="operator_id" placeholder="OP-001" required /></label>
        <label>{t.units}<input name="units_produced" type="number" min="1" required /></label>
        <label className="span2">{t.notes}<input name="qc_notes" placeholder="Optional" /></label>
        <button className="primary" type="submit">{t.save}</button>
      </form>
      <div className="syncBar">Queued offline: {queued} {online && queued > 0 && <button onClick={syncNow}>Sync now</button>} {message && <strong>{message}</strong>}</div>
    </section>
  );
}
