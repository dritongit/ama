import sqlite3
import json
import os

DB_PATH = "data/ama.db"

def init_db():
    # Create tables if they do not exist, safe to call multiple times
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Main table: statements
    cur.execute("""
    CREATE TABLE IF NOT EXISTS statements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        source TEXT DEFAULT 'manual',
        author TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        language TEXT DEFAULT 'sq'
    )
    """)

    # Analysis results table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        statement_id INTEGER,
        defamation_risk TEXT,
        hate_speech INTEGER,
        discrimination INTEGER,
        discrimination_group TEXT,
        discrimination_reason TEXT,
        threats INTEGER,
        threats_reason TEXT,
        legitimate_criticism INTEGER,
        overall_assessment TEXT,
        constitutional_basis TEXT,
        model_used TEXT,
        method TEXT,
        raw_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(statement_id) REFERENCES statements(id)
    )
    """)

    conn.commit()
    conn.close()
    print(f"DB ready: {DB_PATH}")

def save_analysis(statement_text: str, analysis: dict, source: str = "manual", author: str = None, model_used: str = "aya-expanse:8b"):
    # Save statement + analysis to DB
    # analysis = EXACT JSON returned by model (parsed), saved as-is in raw_json
    # and also split into columns for fast stats
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Save statement
    cur.execute(
        "INSERT INTO statements (text, source, author) VALUES (?, ?, ?)",
        (statement_text, source, author)
    )
    statement_id = cur.lastrowid

    # 2. Extract fields safely - if model returned error JSON, use defaults
    # This prevents crash when analysis has no defamation/hate_speech keys
    defam = analysis.get("defamation", {}) if isinstance(analysis.get("defamation", {}), dict) else {}
    disc = analysis.get("discrimination", {}) if isinstance(analysis.get("discrimination", {}), dict) else {}
    threats = analysis.get("threats", {}) if isinstance(analysis.get("threats", {}), dict) else {}
    legit = analysis.get("legitimate_criticism", {}) if isinstance(analysis.get("legitimate_criticism", {}), dict) else {}
    hate = analysis.get("hate_speech", {}) if isinstance(analysis.get("hate_speech", {}), dict) else {}

    # Handle protected_group being None, string, or dict
    group = disc.get("protected_group")
    if isinstance(group, dict):
        group = str(group)
    if group is None:
        group = None
    else:
        group = str(group)

    cur.execute("""
    INSERT INTO analysis_results (
        statement_id, defamation_risk,
        hate_speech, discrimination, discrimination_group, discrimination_reason,
        threats, threats_reason,
        legitimate_criticism, overall_assessment,
        constitutional_basis, model_used, method, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        statement_id,
        str(defam.get("risk", "unknown")),
        1 if hate.get("detected") else 0,
        1 if disc.get("detected") else 0,
        group,
        str(disc.get("reason", "")) if disc.get("reason") else None,
        1 if threats.get("detected") else 0,
        str(threats.get("reason", "")) if threats.get("reason") else None,
        1 if legit.get("is_legitimate") else 0,
        str(analysis.get("overall_assessment", "")) if analysis.get("overall_assessment") else None,
        json.dumps(analysis.get("constitutional_basis", []), ensure_ascii=False),
        model_used,
        "hybrid",
        json.dumps(analysis, ensure_ascii=False)
    ))

    conn.commit()
    conn.close()
    print(f"[DB] Saved statement_id={statement_id}")
    return statement_id

def get_discriminatory_stats():
    # Calculate stats for dashboard
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM statements")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM analysis_results WHERE discrimination = 1")
    disc_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM analysis_results WHERE hate_speech = 1")
    hate_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM analysis_results WHERE threats = 1")
    threat_count = cur.fetchone()[0]
    cur.execute("""
    SELECT discrimination_group, COUNT(*) as c
    FROM analysis_results
    WHERE discrimination = 1 AND discrimination_group IS NOT NULL
    GROUP BY discrimination_group ORDER BY c DESC
    """)
    by_group = cur.fetchall()
    conn.close()
    return {
        "total_statements": total,
        "discriminatory": disc_count,
        "hate_speech": hate_count,
        "threats": threat_count,
        "by_group": by_group,
    }

if __name__ == "__main__":
    init_db()
    print("DB created.")
    print(get_discriminatory_stats())