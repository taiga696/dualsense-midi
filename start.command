#!/bin/bash
# Start the DualSense -> MIDI bridge.
# Double-click friendly. Refuses to start a second copy.
#
# Logs are suppressed with --quiet. Drop the flag if you want to watch
# the button / axis numbers go by.

cd "$(dirname "$0")" || exit 1

pick_python() {
  for candidate in "$HOME/.dualsense-midi-venv/bin/python" \
                   "./venv/bin/python" \
                   "python3"; do
    if command -v "$candidate" > /dev/null 2>&1 \
       && "$candidate" -c "import pygame, rtmidi" > /dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
  echo "python3"
}
PY="$(pick_python)"

if pgrep -f dualsense_midi.py > /dev/null; then
  echo "DualSense MIDI is already running. PID: $(pgrep -f dualsense_midi.py | tr '\n' ' ')"
  echo "Use stop.command to stop it."
  exit 0
fi

echo "Starting DualSense MIDI (Ctrl+C or stop.command to stop)"
exec "$PY" dualsense_midi.py --quiet
