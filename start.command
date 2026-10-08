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
LABEL="com.dualsense.midi"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

# If it was installed as a LaunchAgent, hand control back to launchd instead
# of running a second, unmanaged copy.
if [ -f "$PLIST" ]; then
  echo "LaunchAgent found - starting via launchd..."
  launchctl bootstrap "gui/$UID" "$PLIST" > /dev/null 2>&1 \
    || launchctl load -w "$PLIST" > /dev/null 2>&1
  sleep 3
  if pgrep -f dualsense_midi.py > /dev/null; then
    echo "DualSense MIDI is running (managed by launchd)."
  else
    echo "!! launchd did not start it. Check: tail -20 $(pwd)/bridge.log"
  fi
  exit 0
fi

if pgrep -f dualsense_midi.py > /dev/null; then
  echo "DualSense MIDI is already running. PID: $(pgrep -f dualsense_midi.py | tr '\n' ' ')"
  echo "Use stop.command to stop it."
  exit 0
fi

echo "Starting DualSense MIDI (Ctrl+C or stop.command to stop)"
exec "$PY" dualsense_midi.py --quiet
