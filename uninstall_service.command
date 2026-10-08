#!/bin/bash
# Remove the LaunchAgent installed by install_service.command.
# The bridge stops running and no longer starts at login.

set -u

LABEL="com.dualsense.midi"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "Removing DualSense MIDI LaunchAgent..."

launchctl bootout "gui/$UID/$LABEL" > /dev/null 2>&1
launchctl unload "$PLIST" > /dev/null 2>&1
rm -f "$PLIST"

pkill -f dualsense_midi.py 2>/dev/null

if launchctl list | grep -q "$LABEL"; then
  echo "!! still listed in launchd"
else
  echo "Removed. It will no longer start at login."
  echo "Use start.command to run the bridge by hand."
fi
