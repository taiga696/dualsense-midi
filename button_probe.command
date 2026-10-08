#!/bin/bash
# ボタン/軸の生番号を調べます（ダブルクリックで実行）
# ✕ を押したときに表示される BUTTON 番号が mapping.json の "1" と違えば入れ替えてください
cd "$(dirname "$0")" || exit 1
if [ -x "$HOME/.dualsense-midi-venv/bin/python" ]; then
  PY="$HOME/.dualsense-midi-venv/bin/python"
elif [ -x "/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python" ]; then
  PY="/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python"
else
  PY=python3
fi
exec "$PY" dualsense_midi.py --probe
