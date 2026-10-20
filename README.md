# NetWatch 🔍

:TODO remove vendors and add some more features!!

A home network monitoring tool with a C++ scanner engine and a Python/Flask dashboard. Discovers devices on your local network, fingerprints them by hostname, MAC address, vendor, and open ports, and displays everything in a browser.

---

## Quick Start

```bash
git clone https://github.com/Dzzjio/dzzNetWatch
cd dzzNetWatch
chmod +x install.sh && ./install.sh
./run.sh
```

Open `http://localhost:5000` in your browser. Click **Run New Scan**.

> Must be run on the same machine connected to the network you want to scan. Only scan networks you own or have permission to scan.

---

## How It Works

### 1. Host Discovery — ICMP Ping
Iterates every IP in the detected subnet and sends an ICMP echo request. Devices that reply are alive.

```
Your machine              Target device
    |                          |
    |── ICMP Echo Request ────>|   "are you there?"
    |<─ ICMP Echo Reply ───────|   "yes"  ← host UP
    |                          |
    |── ICMP Echo Request ────>|   (timeout) ← host DOWN
```

### 2. Subnet Auto-Detection
Runs `ip addr` at scan time, parses the active interface IP and prefix, calculates the full host range automatically. No hardcoded IPs.

```
ip addr output:  172.20.10.2/28
prefix /28    →  2^4 - 2 = 14 hosts
scan range    →  172.20.10.1 to 172.20.10.14
```

### 3. MAC Address — ARP Table
After a ping, the OS caches the device's MAC in `/proc/net/arp`. We read it directly — no extra network request needed.

```
Your machine              Target device
    |                          |
    |── ARP: who has .10.1? ──>|   broadcast
    |<─ "that's me: 9e:fa:76"  |   reply
    |                          |
    └── cached in /proc/net/arp
```

### 4. Vendor Lookup — OUI Database
First 3 bytes of a MAC identify the manufacturer. Looked up against the Wireshark OUI database.

```
MAC:  d8:80:83:d0:03:87
OUI:  D8:80:83  →  Intel Corporation
```

> iPhones use MAC randomization — vendor will show as unknown. This is expected behavior.

### 5. Port Scanning — TCP Connect
Attempts a TCP handshake on common ports to identify running services.

```
Your machine         Target
    |── SYN ────────>|
    |<─ SYN+ACK ─────|  ← port OPEN
    |── ACK ────────>|

    |── SYN ────────>|
    |<─ RST ──────────|  ← port CLOSED
```

### 6. Device Fingerprinting
Combines open ports + vendor to guess device type:

| Port  | Service     | Device              |
|-------|-------------|---------------------|
| 22    | SSH         | Linux / Mac machine |
| 80    | HTTP        | Router / web server |
| 135   | RPC         | Windows machine     |
| 445   | SMB         | Windows machine     |
| 3306  | MySQL       | Database server     |
| 7000  | AirPlay     | Apple device        |
| 9100  | Printer     | Network printer     |
| 62078 | iTunes sync | iPhone              |

---

## Stack

| Layer     | Technology            | Purpose                          |
|-----------|-----------------------|----------------------------------|
| Scanner   | C++                   | Ping, ARP, port scanning         |
| Bridge    | Python                | Runs scanner, parses output      |
| Storage   | SQLite                | Stores scan history by session   |
| Dashboard | Python + Flask + HTML | View results in browser          |

---

## Project Structure

```
netwatch/
  scanner/
    main.cpp        ← scan loop, spinner animation, CLI args
    scanner.cpp     ← all network functions
    scanner.h       ← function declarations
  bridge/
    scan_runner.py  ← runs C++ binary, parses output, saves to DB
    db.py           ← SQLite layer
  web/
    app.py          ← Flask server
    templates/
      dashboard.html
      scanning.html
      history.html
    static/
      style.css
  install.sh        ← installs dependencies, compiles scanner
  run.sh            ← launches dashboard
  README.md
```

---

## Requirements

- Linux (Ubuntu 20.04+)
- g++
- Python 3
- pip3

All installed automatically by `install.sh`.

---

## Legal Note

Only scan networks you own or have explicit permission to scan. Scanning public or university networks without permission may violate local laws and terms of service.