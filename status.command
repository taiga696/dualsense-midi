#!/bin/bash
# Show whether the DualSense -> MIDI setup is healthy.
#
# The number that matters is "restarts": if it keeps going up while you are
# using the controller, the bridge is dying and the MIDI port is being
# recreated - which is what makes apps like djay lose the device.

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/bridge.log"

echo "=============================================="
echo " DualSense MIDI - status"
echo "=============================================="

# ------------------------------------------------------------ bridge
PIDS=$(pgrep -f dualsense_midi.py)
if [ -n "$PIDS" ]; then
  FIRST=$(echo "$PIDS" | awk '{print $1}')
  UP=$(ps -o etime= -p "$FIRST" 2>/dev/null | tr -d ' ')
  echo "[bridge]  running  pid=$FIRST  uptime=${UP:-unknown}"
else
  echo "[bridge]  NOT RUNNING"
fi

# ------------------------------------------------------------ launchd
if [ -f "$HOME/Library/LaunchAgents/com.dualsense.midi.plist" ]; then
  echo "[launchd] installed (auto-start at login: yes)"
else
  echo "[launchd] not installed (start it by hand: ./start.command)"
fi

# ------------------------------------------------------------ port
PY="$HOME/.dualsense-midi-venv/bin/python"
[ -x "$PY" ] || PY=python3
"$PY" - <<'PYCODE' 2>/dev/null
import rtmidi
ports = rtmidi.MidiIn().get_ports()
hit = [p for p in ports if "DualSense" in p]
print("[port]    " + (("visible: " + hit[0]) if hit else "MISSING"))
PYCODE

# ------------------------------------------------------------ transport
# With the USB-C cable plugged in, macOS moves the controller off Bluetooth
# by itself, so "Not Connected" there is normal. Check USB first.
if ioreg -p IOUSB -w0 -l 2>/dev/null | grep -qi "DualSense"; then
  LINK="USB (wired)"
else
  BT=$(system_profiler SPBluetoothDataType 2>/dev/null | awk '
    /Connected:/     { sec = "Connected" }
    /Not Connected:/ { sec = "Disconnected" }
    /DualSense/      { print sec }
  ')
  LINK="Bluetooth ${BT:-not found}"
fi
echo "[link]    ${LINK}"

# ------------------------------------------------------------ history
if [ -f "$LOG" ]; then
  RESTARTS=$(grep -c "Virtual MIDI port created" "$LOG")
  echo "[log]     restarts so far: $RESTARTS   ($LOG)"
  LAST=$(grep -E "btn |axis " "$LOG" | tail -1)
  echo "[log]     last input: ${LAST:-none yet}"
  if [ -n "$LAST" ]; then
    echo "[log]     -> input is flowing"
  fi
fi

echo "=============================================="
echo " Healthy = running + port visible + link found"
echo "          + restarts NOT increasing while you play"
echo "=============================================="
