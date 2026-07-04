import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bridge'))

from flask import Flask, render_template, jsonify, redirect, url_for
from db import init_db, get_latest_scan, get_all_scans
from scan_runner import run_scan

app = Flask(__name__)

# global scan state
scan_state = {
    "running": False,
    "done": False,
    "found": 0
}

def run_scan_thread():
    global scan_state
    scan_state["running"] = True
    scan_state["done"] = False
    devices = run_scan()
    scan_state["found"] = len(devices)
    scan_state["running"] = False
    scan_state["done"] = True

@app.route('/')
def dashboard():
    init_db()
    devices = get_latest_scan()
    return render_template('dashboard.html', devices=devices, scanning=scan_state["running"])

@app.route('/scan')
def trigger_scan():
    global scan_state
    if not scan_state["running"]:
        t = threading.Thread(target=run_scan_thread)
        t.daemon = True
        t.start()
    return render_template('scanning.html')

@app.route('/scan/status')
def scan_status():
    return jsonify(scan_state)

@app.route('/api/devices')
def api_devices():
    devices = get_latest_scan()
    return jsonify([dict(d) for d in devices])

@app.route('/history')
def history():
    rows = get_all_scans()
    return render_template('history.html', rows=rows)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)