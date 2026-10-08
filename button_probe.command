#!/bin/bash
# Print the raw button / axis numbers as you press them.
# If the number printed when you press Cross differs from index "1" in
# mapping.json, edit mapping.json to match.

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

exec "$PY" dualsense_midi.py --probe
