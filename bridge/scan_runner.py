import subprocess
import os
import re
from db import init_db, save_device

SCANNER_PATH = os.path.join(os.path.dirname(__file__), '..', 'scanner', 'netwatch')

def detect_subnet():
    """
    runs ip addr, finds the active interface,
    returns base IP and range to scan.
    """
    result = subprocess.run(
        ["ip", "addr"],
        capture_output=True, text=True
    )

    lines = result.stdout.splitlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("inet "):
            continue

        # skip loopback and virtual interfaces
        if "127.0.0.1" in line or "virbr" in line:
            continue

        # extract IP/prefix like "172.20.10.2/28"
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', line)
        if not match:
            continue

        ip = match.group(1)
        prefix = int(match.group(2))

        # skip link-local
        if ip.startswith("169.254"):
            continue

        # calculate range from prefix
        host_bits = 32 - prefix
        total_hosts = (1 << host_bits) - 2  # 2^host_bits - 2

        octets = ip.split('.')

        if prefix >= 24:
            # /24 to /28 — only last octet varies
            base = f"{octets[0]}.{octets[1]}.{octets[2]}."
            return base, 1, total_hosts, f"{base}0/{prefix}"

        elif prefix >= 16:
            # /16 to /23 — third and fourth octet vary
            base = f"{octets[0]}.{octets[1]}."
            return base, 1, total_hosts, f"{base}0.0/{prefix}"

        else:
            # bigger than /16 — too large, cap at 4094
            base = f"{octets[0]}.{octets[1]}."
            return base, 1, 4094, f"{base}0.0/{prefix} (capped)"

    # fallback to hotspot default
    return "172.20.10.", 1, 14, "172.20.10.0/28 (fallback)"


def parse_output(output):
    """
    parse the C++ scanner stdout into a list of device dicts.

    expected format per device:
      ✓  172.20.10.1
           hostname : _gateway
           device   : iPhone
           mac      : 9e:fa:76:b8:ae:64
           vendor   : unknown
           ports    : 62078
    """
    devices = []
    current = {}

    for line in output.splitlines():
        line = line.strip()

        # new device block starts with checkmark line
        if '✓' in line:
            if current:
                devices.append(current)
            parts = line.split()
            ip = parts[-1] if parts else ''
            current = {'ip': ip}

        elif line.startswith('hostname'):
            current['hostname'] = line.split(':', 1)[-1].strip()

        elif line.startswith('device'):
            current['device'] = line.split(':', 1)[-1].strip()

        elif line.startswith('mac'):
            current['mac'] = line.split(':', 1)[-1].strip()

        elif line.startswith('vendor'):
            current['vendor'] = line.split(':', 1)[-1].strip()

        elif line.startswith('ports'):
            current['ports'] = line.split(':', 1)[-1].strip()

    # don't forget the last device
    if current and 'ip' in current:
        devices.append(current)

    return devices


def run_scan():
    """run the C++ scanner and save results to SQLite"""
    # auto detect subnet
    base, start, end, cidr = detect_subnet()
    print(f"detected subnet: {cidr}")
    print(f"scanning {end - start + 1} hosts...")

    if not os.path.exists(SCANNER_PATH):
        print(f"scanner binary not found at {SCANNER_PATH}")
        print("compile it first: cd scanner && g++ main.cpp scanner.cpp -o netwatch -pthread")
        return []

    # run the C++ binary, pass subnet as arguments
    result = subprocess.run(
        [SCANNER_PATH, base, str(start), str(end)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"scanner error: {result.stderr}")
        return []

    print("scan complete, parsing output...")
    devices = parse_output(result.stdout)

    # save each device to database
    init_db()
    for d in devices:
        save_device(
            ip       = d.get('ip', ''),
            hostname = d.get('hostname', 'unknown'),
            device   = d.get('device', 'unknown'),
            mac      = d.get('mac', 'unknown'),
            vendor   = d.get('vendor', 'unknown'),
            ports    = d.get('ports', 'none')
        )
        print(f"  saved: {d.get('ip')} | {d.get('device')}")

    return devices


if __name__ == "__main__":
    devices = run_scan()
    print(f"\nfound {len(devices)} device(s)")
    for d in devices:
        print(d)