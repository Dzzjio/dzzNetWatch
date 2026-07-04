#!/bin/bash

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

# check if arping is installed
if ! command -v arping &> /dev/null; then
    echo "[+] installing arping..."
    sudo apt-get install -y arping
else
    echo "[✓] arping found"
fi

# install python dependencies
echo "[+] installing python dependencies..."
pip3 install flask --break-system-packages -q

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
if [ ! -f "manuf.txt" ]; then
    echo "[+] downloading OUI vendor database..."
    wget -q https://gitlab.com/wireshark/wireshark/-/raw/master/manuf -O manuf.txt
    if [ $? -eq 0 ]; then
        echo "[✓] vendor database downloaded"
    else
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
