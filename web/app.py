import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bridge'))

from flask import Flask, render_template, jsonify
from db import init_db, get_latest_scan, get_all_scans
from scan_runner import run_scan

app = Flask(__name__)

# global scan state
scan_state = {
    "running": False,
    "done": False,
    "found": 0
}
scan_lock = threading.Lock()

def run_scan_thread():
    found = 0
    try:
        found = len(run_scan())
    except Exception as e:
        # never leave "running" stuck on, or no scan could ever start again
        print(f"scan failed: {e}")
    finally:
        with scan_lock:
            scan_state["found"] = found
            scan_state["running"] = False
            scan_state["done"] = True

@app.route('/')
def dashboard():
    init_db()
    devices = get_latest_scan()
    return render_template('dashboard.html', devices=devices, scanning=scan_state["running"])

@app.route('/scan')
def trigger_scan():
    # flip the state here, not in the thread: otherwise two quick requests
    # can both start a scan, and the status page can see the previous
    # scan's done=True and redirect before this one has started
    with scan_lock:
        start = not scan_state["running"]
        if start:
            scan_state["running"] = True
            scan_state["done"] = False
    if start:
        t = threading.Thread(target=run_scan_thread)
        t.daemon = True
        t.start()
    return render_template('scanning.html')

@app.route('/scan/status')
def scan_status():
    with scan_lock:
        return jsonify(dict(scan_state))

@app.route('/api/devices')
def api_devices():
    init_db()
    devices = get_latest_scan()
    return jsonify([dict(d) for d in devices])

@app.route('/history')
def history():
    init_db()
    rows = get_all_scans()
    return render_template('history.html', rows=rows)

if __name__ == '__main__':
    init_db()
    # the debugger allows arbitrary code execution, so never expose it on
    # the network by default; set NETWATCH_HOST=0.0.0.0 to share the dashboard
    host = os.environ.get('NETWATCH_HOST', '127.0.0.1')
    debug = os.environ.get('NETWATCH_DEBUG') == '1'
    app.run(debug=debug, host=host, port=5000)