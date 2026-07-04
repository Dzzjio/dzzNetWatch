#!/bin/bash

echo ""
echo "======================================="
echo "  NetWatch — Starting"
echo "======================================="
echo ""

# check scanner binary exists
if [ ! -f "scanner/netwatch" ]; then
    echo "[✗] scanner not compiled, run ./install.sh first"
    exit 1
fi

echo "[✓] scanner ready"
echo "[+] starting dashboard at http://localhost:5000"
echo "[+] press Ctrl+C to stop"
echo ""

cd web
python3 app.py
