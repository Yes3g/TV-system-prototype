#!/bin/bash
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  python3 start_server.py
else
  echo "Python 3 is required to run the NetVision local server."
  echo "Install Python 3 or run this prototype from Visual Studio Code with Live Server."
  read -r -p "Press Enter to close this window."
fi
