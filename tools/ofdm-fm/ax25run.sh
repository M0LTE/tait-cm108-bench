#!/bin/bash
# ax25run.sh TAG ANSWERER CALLER BYTES
S=$(cat /tmp/ofdm-stamp); TAG=$1; A=$2; C=$3; B=$4
declare -A H=([r1]=radio1 [r2]=radio2) SER=([r1]=20000005 [r2]=20000002) CALL=([r1]=M0LTE-1 [r2]=M0LTE-2)
dev() { echo "--device plughw:CARD=Tait${SER[$1]},DEV=0 --ptt cm108:/dev/tait-ptt-${SER[$1]} --call ${CALL[$1]}"; }
rssi() { echo "RSSI $1 $(date -u +%T.%N | cut -c1-11): $(ssh pi@${H[$1]} "python3 tait-pair/ccdi.py /dev/serial/by-id/usb-M9TWM_TaitInterface_${SER[$1]}-I-if00-port0 q5064")"; }
AL=~/ofdm-bench/$S-$TAG-$A-answer.log
ssh pi@${H[$A]} "timeout 240 ~/pdn-ofdm/pdn-ofdm answer $(dev $A) --detail --log ~/ofdm-bench/$S-$TAG-$A-answer.log --record ~/ofdm-bench/$S-$TAG-$A-answer.wav > /dev/null 2>&1; echo ANSWER-EXIT \$?" &
for i in $(seq 1 10); do sleep 1; ssh pi@${H[$A]} "grep -q 'Callsign set' ~/ofdm-bench/$S-$TAG-$A-answer.log 2>/dev/null" && break; done
sleep 2
ssh pi@${H[$A]} "grep -v -E 'alsa:|audio:' ~/ofdm-bench/$S-$TAG-$A-answer.log" || { echo "ANSWERER NOT UP"; wait; exit 1; }
ssh pi@${H[$A]} "top -b -d 2 -n 110 | grep --line-buffered pdn-ofdm | awk '{print \$9}' | tr '\n' ' ' > ~/ofdm-bench/$S-$TAG-$A-cpu.txt" &
ssh pi@${H[$C]} "top -b -d 2 -n 95 | grep --line-buffered pdn-ofdm | awk '{print \$9}' | tr '\n' ' ' > ~/ofdm-bench/$S-$TAG-$C-cpu.txt" &
ssh pi@${H[$C]} "timeout 200 ~/pdn-ofdm/pdn-ofdm call $(dev $C) --to ${CALL[$A]} --get $B --detail --log ~/ofdm-bench/$S-$TAG-$C-call.log --record ~/ofdm-bench/$S-$TAG-$C-call.wav < /dev/null > /dev/null 2>&1; echo CALL-EXIT \$?"
echo "waiting for answerer timeout"; wait
