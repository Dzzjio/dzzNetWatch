import subprocess
import ipaddress
import os
import re
from db import init_db, start_scan_session, save_device

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SCANNER_PATH = os.path.join(ROOT_DIR, 'scanner', 'netwatch')
MANUF_PATH = os.path.join(ROOT_DIR, 'manuf.txt')

# the scanner is sequential (~1s per dead host), so don't try to sweep a /8
MAX_HOSTS = 4094

VIRTUAL_IFACES = ("lo", "virbr", "docker", "br-", "veth", "tun", "tap")


def _default_iface():
    """name of the interface that holds the default route, or None"""
    result = subprocess.run(
        ["ip", "-o", "-4", "route", "show", "default"],
        capture_output=True, text=True
    )
    match = re.search(r'\bdev (\S+)', result.stdout)
    return match.group(1) if match else None


def detect_subnet():
    """
    runs ip addr, finds the active interface,
    returns the network to scan as an ipaddress.IPv4Network.
    """
    result = subprocess.run(
        ["ip", "-o", "-4", "addr"],
        capture_output=True, text=True
    )

    # e.g. "3: wlo1    inet 172.20.10.2/28 brd ... scope global wlo1"
    candidates = []
    for line in result.stdout.splitlines():
        match = re.search(r'^\d+:\s+(\S+)\s+inet (\d+\.\d+\.\d+\.\d+/\d+)', line)
        if not match:
            continue
        iface, cidr = match.group(1), match.group(2)
        net = ipaddress.ip_interface(cidr).network
        if net.is_loopback or net.is_link_local:
            continue
        candidates.append((iface, net))

    default = _default_iface()
    for iface, net in candidates:
        if iface == default:
            return net
    for iface, net in candidates:
        if not iface.startswith(VIRTUAL_IFACES):
            return net

    # fallback to hotspot default
    return ipaddress.ip_network("172.20.10.0/28")


def scan_ranges(network):
    """
    split a network into (base, start, end) chunks the C++ scanner accepts.
    the scanner only varies the last octet, so anything bigger than a /24
    becomes one call per /24.
    """
    hosts = list(network.hosts())
    if len(hosts) > MAX_HOSTS:
        hosts = hosts[:MAX_HOSTS]

    ranges = []
    for host in hosts:
        octets = str(host).split('.')
        base = '.'.join(octets[:3]) + '.'
        last = int(octets[3])
        if ranges and ranges[-1][0] == base:
            ranges[-1][2] = last
        else:
            ranges.append([base, last, last])
    return [tuple(r) for r in ranges]


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
    network = detect_subnet()
    ranges = scan_ranges(network)
    total = sum(end - start + 1 for _, start, end in ranges)
    print(f"detected subnet: {network}")
    print(f"scanning {total} hosts...")

    if not os.path.exists(SCANNER_PATH):
        print(f"scanner binary not found at {SCANNER_PATH}")
        print("compile it first: cd scanner && g++ main.cpp scanner.cpp -o netwatch -pthread")
        return []

    devices = []
    for base, start, end in ranges:
        # run the C++ binary, pass subnet as arguments
        result = subprocess.run(
            [SCANNER_PATH, base, str(start), str(end), MANUF_PATH],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"scanner error: {result.stderr}")
            return []

        devices.extend(parse_output(result.stdout))

    print("scan complete, saving results...")

    # save each device to database under one scan session
    init_db()
    scan_id = start_scan_session(str(network))
    for d in devices:
        save_device(
            scan_id  = scan_id,
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