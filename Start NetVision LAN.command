#!/bin/bash
cd "$(dirname "$0")" || exit 1
network_ip=""
for interface in en0 en1 en2; do
  network_ip=$(/usr/sbin/ipconfig getifaddr "$interface" 2>/dev/null)
  [ -n "$network_ip" ] && break
done
if [ -z "$network_ip" ]; then
  echo 'Připojte Mac k místní síti. Adresu lze zadat také: python3 start_server.py --lan IP_ADRESA'
else
  python3 start_server.py --lan "$network_ip"
fi
read -r -p 'Stisknutím Enter zavřete okno. '
