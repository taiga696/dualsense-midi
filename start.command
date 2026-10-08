#!/bin/bash
# DualSense -> MIDI ブリッジを起動します（ダブルクリックでも実行できます）
# ・すでに動いている場合は二重起動しません
# ・ログは --quiet で抑制しています（ボタン番号を確認したい時は --quiet を外してください）
cd "$(dirname "$0")" || exit 1
if [ -x "$HOME/.dualsense-midi-venv/bin/python" ]; then
  PY="$HOME/.dualsense-midi-venv/bin/python"
elif [ -x "/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python" ]; then
  PY="/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python"
else
  PY=python3
fi

if pgrep -f dualsense_midi.py > /dev/null; then
  echo "DualSense MIDI はすでに起動中です。PID: $(pgrep -f dualsense_midi.py | tr '\n' ' ')"
  echo "止める時は stop.command を使ってください。"
  exit 0
fi

echo "DualSense MIDI を起動します（停止するには Ctrl+C か stop.command）"
exec "$PY" dualsense_midi.py --quiet
