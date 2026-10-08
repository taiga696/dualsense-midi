#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仮想 MIDI ポート "DualSense MIDI" から届くメッセージを表示する動作確認用モニタ。

使い方:
    python3 midi_monitor.py [秒数]
"""
import sys
import time

import rtmidi

TARGET = "DualSense MIDI"
SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0


def describe(msg):
    if not msg:
        return ""
    st, d1, d2 = msg[0], (msg[1] if len(msg) > 1 else 0), (msg[2] if len(msg) > 2 else 0)
    kind, chan = st & 0xF0, (st & 0x0F) + 1
    if kind in (0x90, 0x80):
        act = "Note ON " if (kind == 0x90 and d2 > 0) else "Note OFF"
        return f"{act} note={d1:<3} vel={d2:<3} ch={chan}"
    if kind == 0xB0:
        return f"CC       cc={d1:<3} val={d2:<3} ch={chan}"
    return f"raw {list(msg)}"


def main():
    # CoreMIDI のポート一覧はクライアント生成時のスナップショットになるため、
    # 見つかるまで再スキャンする
    mi = None
    idx, port_label = None, None
    deadline = time.time() + 20.0
    while time.time() < deadline:
        cand = rtmidi.MidiIn()
        ports = cand.get_ports()
        hit = next((i for i, p in enumerate(ports) if TARGET in p), None)
        if hit is not None:
            mi, idx, port_label = cand, hit, ports[hit]
            print("検出された MIDI 入力ポート:")
            for p in ports:
                print(f"  - {p}")
            break
        del cand
        time.sleep(0.5)
    if idx is None:
        print(f"\n!! '{TARGET}' が見つかりません。dualsense_midi.py を先に起動してください。")
        return 1
    mi.open_port(idx)
    print(f"\n'{port_label}' を監視中（{SECONDS}秒）...\n")
    end = time.time() + SECONDS
    count = 0
    while time.time() < end:
        m = mi.get_message()
        if m:
            count += 1
            print(f"  {describe(m[0])}", flush=True)
        time.sleep(0.005)
    print(f"\n受信メッセージ数: {count}")
    if count == 0:
        print("（0件です。コントローラのボタンやスティックを動かすと表示されます）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
