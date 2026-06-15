#!/bin/bash
echo "Starting Fatura AI Agent Dashboard at http://localhost:7070"
open http://localhost:7070
python3 "$(dirname "$0")/server.py"
