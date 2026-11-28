#!/bin/bash
# pingrun.sh TAG LISTENER PINGER COUNT [SIZE]   LISTENER/PINGER = r1|r2
S=$(cat /tmp/ofdm-stamp); TAG=$1; L=$2; P=$3; N=$4; SZ=${5:-32}
declare -A H=([r1]=radio1 [r2]=radio2) SER=([r1]=20000005 [r2]=20000002) CALL=([r1]=M0LTE-1 [r2]=M0LTE-2)
dev() { echo "--device plughw:CARD=Tait${SER[$1]},DEV=0 --ptt cm108:/dev/tait-ptt-${SER[$1]} --call ${CALL[$1]}"; }
rssi() { echo "RSSI $1 $(date -u +%T.%N | cut -c1-11): $(ssh pi@${H[$1]} "python3 tait-pair/ccdi.py /dev/serial/by-id/usb-M9TWM_TaitInterface_${SER[$1]}-I-if00-port0 q5064")"; }
LT=${LT:-150}; PT=${PT:-120}
ssh pi@${H[$L]} "timeout $LT ~/pdn-ofdm/pdn-ofdm listen $(dev $L) --detail --log ~/ofdm-bench/$S-$TAG-$L-listen.log --record ~/ofdm-bench/$S-$TAG-$L-listen.wav > /dev/null 2>&1; echo LISTEN-EXIT \$?" &
for i in 1 2 3 4 5 6 7 8; do sleep 1; ssh pi@${H[$L]} "grep -q 'Listening as' ~/ofdm-bench/$S-$TAG-$L-listen.log 2>/dev/null" && break; done
ssh pi@${H[$L]} "grep 'Listening as' ~/ofdm-bench/$S-$TAG-$L-listen.log" || { echo "LISTENER NOT UP"; wait; exit 1; }
ssh pi@${H[$L]} "top -b -d 2 -n $((LT/2-5)) | grep --line-buffered -E 'pdn-ofdm' | awk '{print \$9}' | tr '\n' ' ' > ~/ofdm-bench/$S-$TAG-$L-cpu.txt" &
ssh pi@${H[$P]} "top -b -d 2 -n $((PT/2)) | grep --line-buffered -E 'pdn-ofdm' | awk '{print \$9}' | tr '\n' ' ' > ~/ofdm-bench/$S-$TAG-$P-cpu.txt" &
ssh pi@${H[$P]} "timeout $PT ~/pdn-ofdm/pdn-ofdm ping $(dev $P) --to ${CALL[$L]} --count $N --size $SZ --detail --log ~/ofdm-bench/$S-$TAG-$P-ping.log --record ~/ofdm-bench/$S-$TAG-$P-ping.wav > /dev/null 2>&1; echo PING-EXIT \$?" &
PING=$!
( sleep 8; rssi $L; sleep 2; rssi $L; sleep 7; rssi $P; sleep 2; rssi $P ) &
wait $PING
echo "waiting for listener timeout"; wait
