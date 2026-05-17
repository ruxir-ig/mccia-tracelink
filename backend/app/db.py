from pathlib import Path
import os
import sqlite3

ROOT_DIR = Path(__file__).resolve().parents[2]

# ── Persistent storage path ──────────────────────────────────────
# On Render (or any deployment with a /data mount), use /data for persistence.
# Locally, fall back to the project directory.
_default_db = str(ROOT_DIR / "backend" / "tracelink.sqlite3")
if os.getenv("RENDER"):
    # Render environment detected — use /data if a persistent disk is mounted,
    # otherwise fall back to /tmp (survives within a single deploy lifecycle)
    _data_dir = Path("/data")
    if _data_dir.is_dir():
        _default_db = str(_data_dir / "tracelink.sqlite3")
    else:
        _tmp_dir = Path("/tmp/tracelink")
        _tmp_dir.mkdir(parents=True, exist_ok=True)
        _default_db = str(_tmp_dir / "tracelink.sqlite3")

DB_PATH = Path(os.getenv("DB_PATH", _default_db))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATA_FILES = {
    "raw": ROOT_DIR / "raw_materials_log.csv",
    "production": ROOT_DIR / "production_log.csv",
    "qc": ROOT_DIR / "qc_inspection.csv",
    "dispatch": ROOT_DIR / "dispatch_log.csv",
    "supplier": ROOT_DIR / "supplier_master.csv",
    "complaints": ROOT_DIR / "defect_complaints.csv",
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA cache_size=-16000")  # 16MB page cache
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None
