#!/bin/bash
# DJ セットの準備をまとめて行うコマンド
#   1) DualSense -> MIDI ブリッジを起動（未起動なら）
#   2) djay Pro を起動（すでに起動中なら再起動するか確認）
# ターミナルから「 dj.command 」と打つか、Finder でダブルクリック。

cd "$(dirname "$0")" || exit 1
if [ -x "$HOME/.dualsense-midi-venv/bin/python" ]; then
  PY="$HOME/.dualsense-midi-venv/bin/python"
elif [ -x "/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python" ]; then
  PY="/Users/sugita/.workbuddy/binaries/python/envs/default/bin/python"
else
  PY=python3
fi
APP="djay Pro"

echo "=============================================="
echo " DJ セット準備"
echo "=============================================="

# ---------------------------------------------- 1) ブリッジ
echo "[1/3] MIDI ブリッジ"
if pgrep -f dualsense_midi.py > /dev/null; then
  echo "      すでに起動中です (PID: $(pgrep -f dualsense_midi.py | tr '\n' ' '))"
else
  echo "      起動します..."
  nohup "$PY" dualsense_midi.py --quiet > /dev/null 2>&1 &
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    pgrep -f dualsense_midi.py > /dev/null && break
  done
  if pgrep -f dualsense_midi.py > /dev/null; then
    echo "      起動しました (PID: $(pgrep -f dualsense_midi.py | tr '\n' ' '))"
  else
    echo "      !! 起動に失敗しました。手動で start.command を実行してください。"
  fi
fi

# ---------------------------------------------- 2) コントローラ
echo "[2/3] DualSense 接続チェック"
if system_profiler SPBluetoothDataType 2>/dev/null | grep -q "DualSense Wireless Controller"; then
  echo "      DualSense を検出しました"
else
  echo "      !! DualSense が見つかりません。PS + Create 長押しでペアリングしてください。"
fi

# ---------------------------------------------- 3) djay
echo "[3/3] ${APP}"
if pgrep -x "$APP" > /dev/null; then
  echo "      ${APP} はすでに起動中です。"
  echo "      ※ MIDIポートを認識させるには再起動が必要です。"
  printf "      再起動しますか? [y/N]: "
  read -r ans
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    osascript -e "quit app \"${APP}\"" > /dev/null 2>&1
    sleep 3
    open -a "$APP"
    echo "      ${APP} を再起動しました"
  else
    echo "      再起動しませんでした。認識しない場合は ${APP} を手動で再起動してください。"
  fi
else
  open -a "$APP"
  echo "      ${APP} を起動しました"
fi

echo "=============================================="
echo " 完了。djay の MIDI メニューに 'DualSense MIDI' があればOKです。"
echo "=============================================="
