#!/bin/bash
# Install the bridge as a macOS LaunchAgent:
#   - starts automatically at login
#   - restarts itself if it ever crashes
# so the "DualSense MIDI" port always exists before you open djay.
#
# Double-click, or run: ./install_service.command

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.dualsense.midi"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

# Pick a Python that has pygame + python-rtmidi.
PY="$HOME/.dualsense-midi-venv/bin/python"
if [ ! -x "$PY" ] || ! "$PY" -c "import pygame, rtmidi" > /dev/null 2>&1; then
  PY="$(command -v python3)"
fi

echo "=============================================="
echo " Install DualSense MIDI as a login item"
echo "=============================================="
echo "  python : $PY"
echo "  script : $DIR/dualsense_midi.py"
echo "  plist  : $PLIST"

mkdir -p "$HOME/Library/LaunchAgents"

# Stop the ad-hoc copy so launchd owns the process from now on.
if pgrep -f dualsense_midi.py > /dev/null; then
  echo "[1/3] stopping the manually started bridge..."
  pkill -f dualsense_midi.py
  sleep 1
else
  echo "[1/3] no bridge running"
fi

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>$DIR/dualsense_midi.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$DIR/bridge.log</string>
    <key>StandardErrorPath</key>
    <string>$DIR/bridge.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLISTEOF

echo "[2/3] registering with launchd..."
launchctl bootout "gui/$UID/$LABEL" > /dev/null 2>&1
launchctl unload "$PLIST" > /dev/null 2>&1
if ! launchctl bootstrap "gui/$UID" "$PLIST" > /dev/null 2>&1; then
  launchctl load -w "$PLIST"
fi

echo "[3/3] waiting for it to come up..."
sleep 4
if launchctl list | grep -q "$LABEL"; then
  PID="$(launchctl list | grep "$LABEL" | awk '{print $1}')"
  echo "      running (PID: $PID)"
else
  echo "      !! not registered. Check: tail -30 \"$DIR/bridge.log\""
fi

echo "=============================================="
echo " Done. Restart djay Pro once - it only scans"
echo " MIDI devices at launch."
echo "=============================================="
