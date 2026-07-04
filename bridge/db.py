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
        CREATE TABLE IF NOT EXISTS scans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ip          TEXT NOT NULL,
            hostname    TEXT,
            device      TEXT,
            mac         TEXT,
            vendor      TEXT,
            ports       TEXT,
            scanned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def already_saved_recently(ip):
    """check if this IP was already saved in the last 5 minutes"""
    conn = get_connection()
    row = conn.execute("""
        SELECT id FROM scans
        WHERE ip = ?
        AND scanned_at >= datetime('now', '-5 minutes')
    """, (ip,)).fetchone()
    conn.close()
    return row is not None

def save_device(ip, hostname, device, mac, vendor, ports):
    """insert device only if not already saved recently"""
    if already_saved_recently(ip):
        print(f"  skipping duplicate: {ip}")
        return
    conn = get_connection()
    conn.execute("""
        INSERT INTO scans (ip, hostname, device, mac, vendor, ports)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ip, hostname, device, mac, vendor, ports))
    conn.commit()
    conn.close()

def get_latest_scan():
    conn = get_connection()
    row = conn.execute("""
        SELECT scanned_at FROM scans
        ORDER BY scanned_at DESC LIMIT 1
    """).fetchone()

    if not row:
        conn.close()
        return []

    latest_time = row['scanned_at']
    devices = conn.execute("""
        SELECT * FROM scans
        WHERE scanned_at >= datetime(?, '-5 minutes')
        ORDER BY ip ASC
    """, (latest_time,)).fetchall()
    conn.close()
    return devices

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