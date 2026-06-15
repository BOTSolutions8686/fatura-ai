#!/bin/bash
set -e

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│         🤖  Fatura AI — Agent Dashboard                 │"
echo "│             http://localhost:7070                        │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
echo "  Start each agent with output piped to a log file:"
echo ""
echo "    Agent 1:  <your-command> 2>&1 | tee /tmp/fatura-agent-1.log"
echo "    Agent 2:  <your-command> 2>&1 | tee /tmp/fatura-agent-2.log"
echo "    Agent 3:  <your-command> 2>&1 | tee /tmp/fatura-agent-3.log"
echo "    Agent 4:  <your-command> 2>&1 | tee /tmp/fatura-agent-4.log"
echo ""
echo "  The dashboard auto-detects which logs exist and labels them."
echo ""

open http://localhost:7070
python3 "$(dirname "$0")/server.py"
