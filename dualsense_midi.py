#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DualSense (PS5) -> MIDI bridge for macOS

DualSense は HID ゲームパッドで MIDI を喋れないため、
このブリッジが入力を MIDI に変換し、仮想 MIDI ポート
"DualSense MIDI" として djay Pro などのアプリに見せる。

使い方:
    python3 dualsense_midi.py            # 通常起動
    python3 dualsense_midi.py --probe    # ボタン番号調査モード
    python3 dualsense_midi.py --ports    # MIDI ポート一覧

djay Pro 側:
    メニューバー「MIDI」→ "DualSense MIDI" → Configure... → MIDI Learn
    ※ MIDI マッピングは djay PRO サブスクリプションが必要
"""

import argparse
import json
import os
import signal
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame  # noqa: E402
import rtmidi  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "mapping.json")

# ---------------------------------------------------------------- 既定マッピング
# buttons: SDL の生ボタン番号 -> MIDI ノート番号 / ラベル
# axes   : SDL の生軸番号     -> MIDI CC 番号 / ラベル
DEFAULT_MAPPING = {
    "midi_port_name": "DualSense MIDI",
    "channel": 0,
    "deadzone": 0.08,
    "buttons": {
        "0":  {"note": 38, "label": "□  Square"},
        "1":  {"note": 36, "label": "✕  Cross"},
        "2":  {"note": 37, "label": "○  Circle"},
        "3":  {"note": 39, "label": "△  Triangle"},
        "4":  {"note": 44, "label": "L1"},
        "5":  {"note": 45, "label": "R1"},
        "6":  {"note": 46, "label": "L2 (digital)"},
        "7":  {"note": 47, "label": "R2 (digital)"},
        "8":  {"note": 48, "label": "Create"},
        "9":  {"note": 49, "label": "Options"},
        "10": {"note": 50, "label": "L3"},
        "11": {"note": 51, "label": "R3"},
        "12": {"note": 52, "label": "PS / Menu"},
        "13": {"note": 53, "label": "Mic mute?"},
        "14": {"note": 54, "label": "Touchpad"},
        "15": {"note": 40, "label": "?"},
        "16": {"note": 41, "label": "?"},
    },
    "axes": {
        "0": {"cc": 7,  "label": "Left stick X",  "invert": False},
        "1": {"cc": 8,  "label": "Left stick Y",  "invert": True},
        "2": {"cc": 10, "label": "Right stick X", "invert": False},
        "3": {"cc": 11, "label": "Right stick Y", "invert": True},
        "4": {"cc": 1,  "label": "L2 trigger",    "invert": False},
        "5": {"cc": 2,  "label": "R2 trigger",    "invert": False},
    },
}


def load_mapping() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_MAPPING)
        merged.update(cfg)
        return merged
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MAPPING, f, ensure_ascii=False, indent=2)
    return dict(DEFAULT_MAPPING)


def to_7bit(v: float, invert: bool) -> int:
    """-1.0 .. 1.0 を 0..127 に変換"""
    if invert:
        v = -v
    n = int(round((v + 1.0) / 2.0 * 127))
    return max(0, min(127, n))


class Bridge:
    def __init__(self, cfg: dict, verbose: bool = True):
        self.cfg = cfg
        self.verbose = verbose
        self.channel = int(cfg.get("channel", 0))
        self.deadzone = float(cfg.get("deadzone", 0.08))
        self.bmap = {int(k): v for k, v in cfg.get("buttons", {}).items()}
        self.amap = {int(k): v for k, v in cfg.get("axes", {}).items()}

        self.midi = rtmidi.MidiOut()
        self.port_name = cfg.get("midi_port_name", "DualSense MIDI")
        self.midi.open_virtual_port(self.port_name)

        pygame.init()
        pygame.joystick.init()
        self.joy = None
        self.last_axis = {}
        self.last_btn = {}
        self.running = True

    # ------------------------------------------------------------ MIDI
    def note(self, number: int, on: bool, velocity: int = 100):
        status = 0x90 if on else 0x80
        self.midi.send_message([status | self.channel, number, velocity if on else 0])

    def cc(self, number: int, value: int):
        self.midi.send_message([0xB0 | self.channel, number, value])

    # ------------------------------------------------------------ 入力
    def find_controller(self):
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()
            if "DualSense" in j.get_name() or "PS5" in j.get_name() or "Wireless Controller" in j.get_name():
                return j
        return None

    def run(self):
        print(f"[OK] 仮想 MIDI ポート作成: {self.port_name}")
        while self.running:
            if self.joy is None:
                self.joy = self.find_controller()
                if self.joy is None:
                    print("[..] DualSense を探しています... (PS + Create 長押しでペアリング)", flush=True)
                    time.sleep(2.0)
                    continue
                print(f"[OK] 接続: {self.joy.get_name()} "
                      f"(axes={self.joy.get_numaxes()}, buttons={self.joy.get_numbuttons()})")
                self.last_axis.clear()
                self.last_btn.clear()
                for _ in range(5):
                    pygame.event.pump()
                    time.sleep(0.05)
                for a in range(self.joy.get_numaxes()):
                    self.emit_axis(a)
            try:
                pygame.event.pump()
            except Exception:
                self.joy = None
                continue

            for ev in pygame.event.get():
                if ev.type in (pygame.JOYDEVICEREMOVED, pygame.JOYDEVICEREMOVED):
                    print("[!!] コントローラが切断されました")
                    self.joy = None
            if self.joy is not None:
                self.poll()
            time.sleep(0.005)

    def poll(self):
        """イベントに頼らず毎フレーム状態を読む（取りこぼし防止）"""
        j = self.joy
        try:
            nb = j.get_numbuttons()
            na = j.get_numaxes()
        except Exception:
            self.joy = None
            return
        for b in range(nb):
            try:
                v = j.get_button(b)
            except Exception:
                self.joy = None
                return
            if v != self.last_btn.get(b):
                self.last_btn[b] = v
                self.on_button(b, bool(v))
        for a in range(na):
            self.emit_axis(a)

    def on_button(self, idx: int, down: bool):
        m = self.bmap.get(idx)
        if not m:
            return
        note = int(m["note"])
        self.note(note, down)
        if self.verbose and down:
            print(f"    btn {idx:>2} -> Note {note:<3} {m.get('label','')}", flush=True)

    def emit_axis(self, idx: int):
        if self.joy is None or idx >= self.joy.get_numaxes():
            return
        m = self.amap.get(idx)
        if not m:
            return
        raw = self.joy.get_axis(idx)
        if abs(raw) < self.deadzone:
            raw = 0.0
        val = to_7bit(raw, bool(m.get("invert", False)))
        if self.last_axis.get(idx) == val:
            return
        self.last_axis[idx] = val
        self.cc(int(m["cc"]), val)
        if self.verbose:
            print(f"    axis {idx:>2} -> CC {int(m['cc']):<3} = {val:<4} {m.get('label','')}", flush=True)

    def close(self):
        self.running = False
        try:
            for i in range(16):
                self.note(i, False)
            self.midi.close_port()
        except Exception:
            pass
        pygame.quit()


def probe():
    """ボタン/軸の生番号を調べるモード"""
    pygame.init()
    pygame.joystick.init()
    j = None
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
    if j is None:
        print("コントローラが見つかりません")
        return
    print(f"検出: {j.get_name()} axes={j.get_numaxes()} buttons={j.get_numbuttons()}")
    print("ボタンを押す / スティック・トリガーを動かすと番号が表示されます。Ctrl+C で終了。\n")
    prev = [0] * j.get_numbuttons()
    prevax = [0.0] * j.get_numaxes()
    try:
        while True:
            pygame.event.pump()
            for ev in pygame.event.get():
                if ev.type == pygame.JOYBUTTONDOWN:
                    print(f"  BUTTON {ev.button}", flush=True)
                elif ev.type == pygame.JOYAXISMOTION:
                    if abs(ev.value - prevax[ev.axis]) > 0.15:
                        print(f"  AXIS   {ev.axis}  value={ev.value:.2f}", flush=True)
                        prevax[ev.axis] = ev.value
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("\n終了")
    pygame.quit()


def list_ports():
    mo = rtmidi.MidiOut()
    print("利用可能な MIDI 出力先:")
    for i, p in enumerate(mo.get_ports()):
        print(f"  [{i}] {p}")
    print("\n(仮想ポートは起動後に他アプリから見えるようになります)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="ボタン番号調査モード")
    ap.add_argument("--ports", action="store_true", help="MIDI ポート一覧")
    ap.add_argument("--quiet", action="store_true", help="ログを出さない")
    ap.add_argument("--test", action="store_true", help="動作確認用のテスト信号を送信")
    args = ap.parse_args()

    if args.ports:
        list_ports()
        return
    if args.probe:
        probe()
        return

    cfg = load_mapping()
    b = Bridge(cfg, verbose=not args.quiet)
    if args.test:
        print("[test] Note 36 ON/OFF と CC 1 のスイープを送信します")
        for n in (36, 37, 38, 39):
            b.note(n, True)
            time.sleep(0.4)
            b.note(n, False)
            time.sleep(0.1)
        for v in (0, 64, 127, 64, 0):
            b.cc(1, v)
            time.sleep(0.3)
        print("[test] 送信完了")

    def handler(signum, frame):
        b.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    print(f"[..] {CONFIG_PATH} のマッピングを使用")
    print("[..] djay Pro → メニューバー「MIDI」→ "
          f"\"{cfg.get('midi_port_name')}\" → Configure... で割り当ててください")
    print("[..] 終了は Ctrl+C\n")
    b.run()


if __name__ == "__main__":
    main()
