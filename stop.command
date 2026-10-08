#!/bin/bash
# DualSense -> MIDI ブリッジを停止します
PIDS=$(pgrep -f dualsense_midi.py)
if [ -z "$PIDS" ]; then
  echo "DualSense MIDI は起動していません。"
  exit 0
fi
kill $PIDS
sleep 1
echo "停止しました。PID: $PIDS"
