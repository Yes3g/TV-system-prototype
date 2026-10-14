#!/bin/bash
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 start_server.py
else
  echo "Python 3.10 or newer is required. Install Python, then run this launcher again."
  read -r -p "Press Enter to close this window."
fi
