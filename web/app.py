import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bridge'))

from flask import Flask, render_template, jsonify
from db import init_db, get_latest_scan, get_latest_session, get_history
from scan_runner import run_scan, detect_subnet, scan_ranges

app = Flask(__name__)

# device type (from the C++ guessDevice) -> icon / colour key used by the UI
DEVICE_KINDS = {
    'iPhone':            'phone',
    'Samsung device':    'phone',
    'Apple device':      'apple',
    'Windows machine':   'windows',
    'Linux/Mac machine': 'linux',
    'PC/Laptop':         'laptop',
    'Router/Web server': 'router',
    'Printer':           'printer',
    'Database server':   'database',
}

PORT_NAMES = {
    22: 'SSH', 80: 'HTTP', 135: 'RPC', 443: 'HTTPS', 445: 'SMB',
    3306: 'MySQL', 7000: 'AirPlay', 9100: 'Print', 62078: 'iTunes',
}

@app.template_filter('kind')
def device_kind(device):
    return DEVICE_KINDS.get(device, 'unknown')

@app.template_filter('ports')
def port_list(ports):
    """"22,80" -> [(22, 'SSH'), (80, 'HTTP')]; "none" -> []"""
    result = []
    for p in (ports or '').split(','):
        if p.strip().isdigit():
            result.append((int(p), PORT_NAMES.get(int(p), 'TCP')))
    return result

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
    open_ports = sum(len(port_list(d['ports'])) for d in devices)
    return render_template('dashboard.html', devices=devices,
                           session=get_latest_session(), open_ports=open_ports,
                           scanning=scan_state["running"])

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
    network = detect_subnet()
    hosts = sum(end - start + 1 for _, start, end in scan_ranges(network))
    return render_template('scanning.html', network=network, hosts=hosts)

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
    return render_template('history.html', history=get_history())

if __name__ == '__main__':
    init_db()
    # the debugger allows arbitrary code execution, so never expose it on
    # the network by default; set NETWATCH_HOST=0.0.0.0 to share the dashboard
    host = os.environ.get('NETWATCH_HOST', '127.0.0.1')
    debug = os.environ.get('NETWATCH_DEBUG') == '1'
    app.run(debug=debug, host=host, port=5000)