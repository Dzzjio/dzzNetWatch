import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'netwatch.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            network     TEXT,
            started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id     INTEGER REFERENCES scan_sessions(id),
            ip          TEXT NOT NULL,
            hostname    TEXT,
            device      TEXT,
            mac         TEXT,
            vendor      TEXT,
            ports       TEXT,
            scanned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # migrate databases created before scan sessions existed
    columns = [r['name'] for r in conn.execute("PRAGMA table_info(scans)")]
    if 'scan_id' not in columns:
        conn.execute("ALTER TABLE scans ADD COLUMN scan_id INTEGER REFERENCES scan_sessions(id)")
    conn.commit()
    conn.close()

def start_scan_session(network):
    """create a new scan session and return its id"""
    conn = get_connection()
    cur = conn.execute("INSERT INTO scan_sessions (network) VALUES (?)", (network,))
    conn.commit()
    scan_id = cur.lastrowid
    conn.close()
    return scan_id

def save_device(scan_id, ip, hostname, device, mac, vendor, ports):
    """insert device once per scan session"""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM scans WHERE scan_id = ? AND ip = ?", (scan_id, ip)
    ).fetchone()
    if row is not None:
        print(f"  skipping duplicate: {ip}")
        conn.close()
        return
    conn.execute("""
        INSERT INTO scans (scan_id, ip, hostname, device, mac, vendor, ports)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (scan_id, ip, hostname, device, mac, vendor, ports))
    conn.commit()
    conn.close()

def get_latest_scan():
    """devices found by the most recent scan session only"""
    conn = get_connection()
    devices = conn.execute("""
        SELECT * FROM scans
        WHERE scan_id = (SELECT MAX(id) FROM scan_sessions)
    """).fetchall()
    conn.close()
    # sort numerically: "10.0.0.10" after "10.0.0.9"
    return sorted(devices, key=lambda d: _ip_key(d['ip']))

def _ip_key(ip):
    try:
        return tuple(int(o) for o in ip.split('.'))
    except ValueError:
        return (256,)

def get_scan_history(ip):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM scans
        WHERE ip = ?
        ORDER BY scanned_at DESC
        LIMIT 20
    """, (ip,)).fetchall()
    conn.close()
    return rows

def get_all_scans():
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM scans
        ORDER BY scanned_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return rows