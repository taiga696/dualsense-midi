#!/bin/bash
# Stop the DualSense -> MIDI bridge.
#
# If it is running as a LaunchAgent (install_service.command), killing the
# process is not enough: launchd's KeepAlive immediately restarts it. So we
# unload the agent first, then kill whatever is left.

LABEL="com.dualsense.midi"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST" ]; then
  echo "LaunchAgent found - unloading $LABEL..."
  launchctl bootout "gui/$UID/$LABEL" > /dev/null 2>&1
  launchctl unload "$PLIST" > /dev/null 2>&1
  sleep 1
fi

PIDS=$(pgrep -f dualsense_midi.py)
if [ -z "$PIDS" ]; then
  echo "DualSense MIDI is not running."
  exit 0
fi
kill $PIDS
sleep 1
echo "Stopped. PID: $PIDS"
echo "(It will stay stopped. Run start.command to bring it back.)"
