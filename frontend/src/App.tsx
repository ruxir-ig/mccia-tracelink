import { useEffect, useState } from "react";
import { TraceSearch } from "./components/TraceSearch";
import { ContaminationAlert } from "./components/ContaminationAlert";
import { OperatorEntry } from "./components/OperatorEntry";
import "./styles.css";

export default function App() {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Precision Auto Parts</p>
          <h1>AI-powered batch traceability in under 30 seconds</h1>
          <p>Follow a dispatch order back to raw lot, supplier, machine, shift, operator, and QC outcome. Built for Excel import, paper-record cleanup, and offline shop-floor entry.</p>
        </div>
        <span className={online ? "pill ok" : "pill warn"}>{online ? "Online sync ready" : "Offline mode"}</span>
      </section>
      <div className="grid">
        <TraceSearch />
        <ContaminationAlert />
      </div>
      <OperatorEntry online={online} />
    </main>
  );
}
