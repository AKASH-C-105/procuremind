#!/bin/bash
echo ""
echo " ========================================"
echo "  ProcureMind 2.0 — Starting up..."
echo " ========================================"
echo ""
cd "$(dirname "$0")"
pip install flask flask-cors numpy -q
echo ""
echo " Starting server at http://localhost:5000"
echo " Open your browser to: http://localhost:5000"
echo ""
python3 app.py
