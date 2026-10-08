#!/bin/bash
# One-shot launcher for a DJ session:
#   1) start the DualSense -> MIDI bridge (if not already running)
#   2) check that the DualSense is connected over Bluetooth
#   3) launch djay Pro (or restart it so it picks up the new MIDI port)
#
# Run it from the terminal (`dj.command`), or double-click in Finder.

cd "$(dirname "$0")" || exit 1

# Pick a Python that actually has pygame + python-rtmidi installed.
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
APP="djay Pro"

echo "=============================================="
echo " DualSense MIDI - DJ session setup"
echo "=============================================="

# ------------------------------------------------ 1) bridge
echo "[1/3] MIDI bridge"
if pgrep -f dualsense_midi.py > /dev/null; then
  echo "      already running (PID: $(pgrep -f dualsense_midi.py | tr '\n' ' '))"
else
  echo "      starting..."
  LOG="$(pwd)/bridge.log"
  nohup "$PY" dualsense_midi.py > "$LOG" 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    pgrep -f dualsense_midi.py > /dev/null && break
  done
  if pgrep -f dualsense_midi.py > /dev/null; then
    echo "      started (PID: $(pgrep -f dualsense_midi.py | tr '\n' ' '))"
  else
    echo "      !! failed to start. Run start.command manually to see the error."
  fi
fi

# ------------------------------------------------ 2) controller
echo "[2/3] DualSense connection"
if system_profiler SPBluetoothDataType 2>/dev/null | grep -q "DualSense Wireless Controller"; then
  echo "      DualSense detected"
else
  echo "      !! DualSense not found. Hold PS + Create to pair it."
fi

# ------------------------------------------------ 3) djay
echo "[3/3] ${APP}"
# djay only scans MIDI devices at launch, so a running instance will never
# see the port. Always restart it - that is the whole point of this script.
if pgrep -x "$APP" > /dev/null; then
  echo "      restarting ${APP} (it only scans MIDI devices at launch)..."
  osascript -e "quit app \"${APP}\"" > /dev/null 2>&1
  sleep 4
fi
open -a "$APP"
echo "      ${APP} launched"

echo "=============================================="
echo " Done. In djay: menu bar MIDI -> 'DualSense MIDI'."
echo "=============================================="
