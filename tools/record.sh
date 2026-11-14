#!/usr/bin/env bash
# record.sh <udid> <out.mp4> <maestro output file>: records the simulator screen from the moment Maestro prints
# "Running on" (its driver is up and the flow starts) until a file named stop-recording appears next to <out.mp4>,
# so the video skips the minutes Maestro's driver needs to start. Then shrinks it to 1080 px high.
set -u
udid=$1 out=$2 log=$3
stop="$(dirname "$out")/stop-recording"
until grep -q "Running on" "$log" 2>/dev/null || [ -e "$stop" ]; do sleep 0.2; done
echo "record.sh: recording $(basename "$out") from $(date -u +%T)"
xcrun simctl io "$udid" recordVideo --codec=h264 --force "$out" &
recorder=$!
until [ -e "$stop" ]; do sleep 0.5; done
sleep 2
kill -INT "$recorder"   # SIGINT lets simctl finish the mp4
wait "$recorder"
echo "record.sh: stopped $(basename "$out") at $(date -u +%T)"
# Full-size recordings ran to 460 MB for 8 minutes; Apple's own converter keeps the picture at 1080 px high.
avconvert --preset Preset1920x1080 --source "$out" --output "${out%.mp4}-1080.mp4" && mv "${out%.mp4}-1080.mp4" "$out" \
  || echo "avconvert failed; keeping the full-size $out"
