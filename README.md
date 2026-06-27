# NetWatch 🔍

A home network monitoring tool with a C++ scanner engine that discovers devices, fingerprints them, and reports open services.

---

## How It Works

### 1. Host Discovery — ICMP Ping
The scanner iterates every IP in the subnet and sends an **ICMP echo request** (ping) to each one. If the device replies with an ICMP echo reply, it's alive.

```
Your laptop                Target device
    |                           |
    |──── ICMP Echo Request ───>|   "are you there?"
    |<─── ICMP Echo Reply ──────|   "yes"  ← host is UP
    |                           |
    |──── ICMP Echo Request ───>|   (silence / timeout) ← host is DOWN
```

### 2. Hostname Resolution — Reverse DNS
Once a host is found, we do a **reverse DNS lookup** — instead of asking "what IP does google.com have?", we ask "what name does 172.20.10.1 have?". The OS resolves this via mDNS or the local DNS server (your phone's hotspot in this case).

```
Your laptop                 DNS / mDNS
    |                           |
    |──── who is 172.20.10.1? ─>|
    |<─── "_gateway"  ──────────|
```

### 3. MAC Address — ARP Table
When your laptop pinged a device, the OS needed its **MAC address** to actually send the frame over WiFi. It used **ARP (Address Resolution Protocol)** to find it and cached the result in `/proc/net/arp`.

```
Your laptop                Target device
    |                           |
    |──── ARP: who has .10.1? ─>|   broadcast to everyone
    |<─── "that's me: 9e:fa:76" |   unicast reply
    |                           |
    └── OS caches this in /proc/net/arp
```

We just read that cache — no extra network request needed.

### 4. Vendor Lookup — OUI Database
The first 3 bytes of a MAC address identify the **manufacturer** (OUI — Organizationally Unique Identifier). We look this up against the Wireshark OUI database.

```
MAC:  d8:80:83:d0:03:87
OUI:  D8:80:83  →  Intel Corporation
```

> Note: Modern phones use **MAC randomization** — they generate a fake random MAC per network for privacy. This is why the iPhone shows "unknown" vendor.

### 5. Port Scanning — TCP Connect
For each live host we attempt a **TCP handshake** on common ports. If the connection succeeds, the port is open and a service is running there.

```
Your laptop              Target device
    |                         |
    |──── SYN ───────────────>|   "I want to connect"
    |<─── SYN + ACK ──────────|   "ok"       ← port OPEN
    |──── ACK ───────────────>|
    
    |──── SYN ───────────────>|   "I want to connect"
    |<─── RST ────────────────|   "nothing here"  ← port CLOSED
    
    |──── SYN ───────────────>|   (timeout)   ← FILTERED
```

### 6. Device Fingerprinting
Combining open ports + vendor, we guess the device type:

| Port  | Service       | Likely device        |
|-------|---------------|----------------------|
| 22    | SSH           | Linux / Mac machine  |
| 80    | HTTP          | Router / web server  |
| 443   | HTTPS         | Router / server      |
| 3306  | MySQL         | Database server      |
| 7000  | AirPlay       | Apple device         |
| 9100  | Printer       | Network printer      |
| 62078 | iTunes sync   | iPhone               |

---

## Stack

| Layer      | Technology              | Purpose                        |
|------------|-------------------------|--------------------------------|
| Scanner    | C++                     | Ping, ARP, port scanning       |
| Storage    | Python + SQLite         | Log scan results over time     |
| Dashboard  | Python + Flask + HTML   | View results in browser        |

---

## Project Structure

```
netwatch/
  scanner/
    main.cpp        ← entry point, scan loop, spinner animation
    scanner.cpp     ← all network functions
    scanner.h       ← function declarations
    Makefile        ← build with `make`
  bridge/
    scan_runner.py  ← runs C++ binary, parses output
    db.py           ← SQLite storage
  web/
    app.py          ← Flask server
    templates/
      dashboard.html
    static/
      style.css
  manuf.txt         ← OUI vendor database (not committed, too large)
  README.md
```

---

## Build & Run

```bash
# compile
cd scanner
g++ main.cpp scanner.cpp -o netwatch -pthread

# run
./netwatch
```

---

## Legal Note

Only scan networks you own or have explicit permission to scan. This tool was developed and tested on a personal mobile hotspot.