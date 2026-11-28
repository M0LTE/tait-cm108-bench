#!/bin/bash
# rig.sh: small helpers for the OFDM-FM bench. Run from the session machine, which can ssh to both Pis.
#   rig.sh status     services, processes, PTT devices, RSSI on both
#   rig.sh pttoff     force PTT off on both radios (CM108 GPIO3 low) and read RSSI to confirm
#   rig.sh rssi       one RSSI read each (tenths of dBm; about -125 with nothing on air)
#   rig.sh stop       stop the modem services on both Pis so the sound cards are free
#   rig.sh stamp      start a new set of log names (writes /tmp/ofdm-stamp)
declare -A H=([r1]=radio1 [r2]=radio2) SER=([r1]=20000005 [r2]=20000002) SVC=([r1]=tait-top [r2]=tait-bottom)
port() { echo "/dev/serial/by-id/usb-M9TWM_TaitInterface_${SER[$1]}-I-if00-port0"; }
rssi() { for r in r1 r2; do echo "$r ${H[$r]}: $(ssh pi@${H[$r]} "python3 tait-pair/ccdi.py $(port $r) q5064")"; done; }
pttoff() { for r in r1 r2; do ssh pi@${H[$r]} "python3 -c \"open('/dev/tait-ptt-${SER[$r]}','wb',buffering=0).write(bytes([0,0,0,0x04,0]))\" && echo '$r PTT off'"; done; }
case "$1" in
  rssi) rssi ;;
  pttoff) pttoff; sleep 1; rssi ;;
  stop) for r in r1 r2; do ssh pi@${H[$r]} "sudo systemctl stop pdn-soundmodem@${SVC[$r]}; systemctl is-active pdn-soundmodem@${SVC[$r]}"; done ;;
  stamp) date -u +%Y%m%dT%H%M > /tmp/ofdm-stamp; cat /tmp/ofdm-stamp; for r in r1 r2; do ssh pi@${H[$r]} "mkdir -p ~/ofdm-bench"; done ;;
  status) for r in r1 r2; do echo "== $r ${H[$r]}"; ssh pi@${H[$r]} "systemctl is-active pdn-soundmodem@${SVC[$r]}; pgrep -a pdn-ofdm | cut -c1-80; ls -la /dev/tait-ptt-${SER[$r]} | cut -c40-; aplay -l | grep -i tait; uptime | cut -c1-60"; done; rssi ;;
  *) sed -n 2,7p "$0" ;;
esac
