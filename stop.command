#!/bin/bash
# Stop the DualSense -> MIDI bridge.
PIDS=$(pgrep -f dualsense_midi.py)
if [ -z "$PIDS" ]; then
  echo "DualSense MIDI is not running."
  exit 0
fi
kill $PIDS
sleep 1
echo "Stopped. PID: $PIDS"
