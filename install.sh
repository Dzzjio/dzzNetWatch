#!/bin/bash

# work from the project root no matter where the script is called from
cd "$(dirname "$0")" || exit 1

echo ""
echo "======================================="
echo "  NetWatch — Installation"
echo "======================================="
echo ""

# check if g++ is installed
if ! command -v g++ &> /dev/null; then
    echo "[+] installing g++..."
    sudo apt-get install -y g++
else
    echo "[✓] g++ found"
fi

# check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[+] installing python3..."
    sudo apt-get install -y python3 python3-pip
else
    echo "[✓] python3 found"
fi

# python3 can be present without pip3 (default on Ubuntu)
if ! command -v pip3 &> /dev/null; then
    echo "[+] installing pip3..."
    sudo apt-get install -y python3-pip
else
    echo "[✓] pip3 found"
fi

# check if arping is installed
if ! command -v arping &> /dev/null; then
    echo "[+] installing arping..."
    sudo apt-get install -y arping
else
    echo "[✓] arping found"
fi

# install python dependencies
echo "[+] installing python dependencies..."
# --break-system-packages only exists (and is only needed) on newer pip
if ! pip3 install flask -q 2>/dev/null; then
    pip3 install flask --break-system-packages -q || { echo "[✗] flask install failed"; exit 1; }
fi

# compile C++ scanner
echo "[+] compiling scanner..."
cd scanner
g++ main.cpp scanner.cpp -o netwatch -pthread

if [ $? -eq 0 ]; then
    echo "[✓] scanner compiled"
else
    echo "[✗] compilation failed"
    exit 1
fi

cd ..

# download vendor database
# (the old gitlab.com/wireshark/.../manuf URL returns 404; the file was removed from the repo)
if [ ! -s "manuf.txt" ]; then
    echo "[+] downloading OUI vendor database..."
    # download to a temp file so a failed download doesn't leave an empty manuf.txt behind
    if wget -q https://standards-oui.ieee.org/oui/oui.txt -O manuf.txt.tmp && [ -s manuf.txt.tmp ]; then
        mv manuf.txt.tmp manuf.txt
        echo "[✓] vendor database downloaded"
    else
        rm -f manuf.txt.tmp
        echo "[!] vendor database download failed, vendor lookup will be unavailable"
    fi
else
    echo "[✓] vendor database found"
fi

echo ""
echo "======================================="
echo "  Installation complete!"
echo "  Run: ./run.sh"
echo "======================================="
echo ""
