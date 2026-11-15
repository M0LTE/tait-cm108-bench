# Source this on a machine that can ssh to both Pis. Top radio (19925369) is on radio1 with the RSP1; bottom (19925328) on radio2.
R1=pi@radio1; R2=pi@radio2; D=tait-pair
top=("$R1" /dev/tait-ptt-20000002 Tait20000002 tait-top); bot=("$R2" /dev/tait-ptt-20000005 Tait20000005 tait-bottom)
GAIN=${GAIN:-IFGR=30,RFGR=0}
modems() { ssh $R1 "sudo systemctl $1 pdn-soundmodem@tait-top"; ssh $R2 "sudo systemctl $1 pdn-soundmodem@tait-bottom"; }
# sdr TAG SECONDS : RSP1 capture to ~/tait-pair/TAG.cf32 on radio1 (returns when it ends)
sdr() { ssh $R1 "cd $D && rm -f $1.cf32 && rx_sdr -d driver=sdrplay -f 146440000 -s 192000 -g $GAIN -F CF32 -n $((192000*$2)) $1.cf32 >/dev/null 2>&1"; }
# rec top|bot TAG SECONDS : record that radio's receive audio to ~/tait-pair/TAG.wav on its Pi
rec() { local -n r=$1; ssh ${r[0]} "cd $D && arecord -q -D plughw:CARD=${r[2]},DEV=0 -f S16_LE -r 48000 -c 1 -d $3 $2.wav"; }
# tx top|bot GEN-ARGS... : generate a test WAV on that radio's Pi and transmit it (modems must be stopped)
tx() { local -n r=$1; shift; ssh ${r[0]} "cd $D && python3 gen.py $1 /tmp/bench.wav ${*:2} && python3 play.py ${r[1]} ${r[2]} /tmp/bench.wav"; }
# shot TXRADIO TAG SECONDS GEN-ARGS... : RSP1 + the other radio's audio, both for SECONDS, around one transmission
shot() { local t=$1 tag=$2 secs=$3; shift 3; local o=bot; [ $t = bot ] && o=top
  sdr $tag $((secs+6)) & rec $o $tag $((secs+4)) & sleep 5; tx $t "$@"; wait; }
# drive top|bot DB : set that station's playback level through the modem's API (not persisted)
drive() { local -n r=$1; local port=8117; [ $1 = bot ] && port=8107
  ssh ${r[0]} "K=\$(sudo python3 -c \"import json;print(json.load(open('/etc/pdn-soundmodem/${r[3]}.json'))['api']['key'])\"); curl -s -o /dev/null -X POST -H \"Authorization: Bearer \$K\" -H 'Content-Type: application/json' -d '{\"playbackDb\": $2}' 'http://127.0.0.1:$port/api/mixer?persist=false'"; }
# mode MODE : put both stations on one ofdm-fm preset (edits the config file's first modem and restarts)
mode() { local m=$1 h; for h in "$R1 tait-top" "$R2 tait-bottom"; do set -- $h; ssh $1 "sudo sed -i -E '0,/\"mode\": *\"[^\"]+\"/s//\"mode\": \"$m\"/' /etc/pdn-soundmodem/$2.json && sudo systemctl restart pdn-soundmodem@$2"; done; sleep 10; }
# frames N SIZE ROUNDS DB... : N UI frames of SIZE bytes each way at each drive level, ROUNDS times interleaved.
# Prints each run as it finishes, then totals. Slow when frames are lost (each run then waits out its timeout).
frames() { local n=$1 size=$2 rounds=$3 i db a b; shift 3; local w=$((n*12/10+10)); declare -A bt tb
  for ((i=1;i<=rounds;i++)); do for db in "$@"; do drive top $db; drive bot $db
    a=$(ssh $R1 "python3 $D/kisstest.py radio2:8105 127.0.0.1:8115 $n $size $w" | sed -E 's/.*"delivered": ([0-9]+).*/\1/')
    b=$(ssh $R1 "python3 $D/kisstest.py 127.0.0.1:8115 radio2:8105 $n $size $w" | sed -E 's/.*"delivered": ([0-9]+).*/\1/')
    echo "round $i drive $db dB: bottom->top $a/$n, top->bottom $b/$n"
    bt[$db]=$((${bt[$db]:-0}+a)); tb[$db]=$((${tb[$db]:-0}+b)); done; done
  drive top 0; drive bot 0
  for db in "$@"; do echo "TOTAL drive $db dB, $size B: bottom->top ${bt[$db]}/$((n*rounds)), top->bottom ${tb[$db]}/$((n*rounds))"; done; }
