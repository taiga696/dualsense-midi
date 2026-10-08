#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DualSense (PS5) -> MIDI bridge for macOS

A DualSense is an HID gamepad: it speaks HID, not MIDI. That is why a
Bluetooth-paired DualSense never shows up as a MIDI device in djay,
Ableton, Logic, etc. This bridge reads the gamepad and re-emits every
input as MIDI on a Core MIDI *virtual* port, so any app sees it as a
normal MIDI controller. No IAC Driver configuration required.

Usage:
    python3 dualsense_midi.py            # run the bridge
    python3 dualsense_midi.py --probe    # print raw button/axis numbers
    python3 dualsense_midi.py --ports    # list MIDI destinations
    python3 dualsense_midi.py --test     # send a test pattern
    python3 dualsense_midi.py --quiet    # run without input logging

In djay Pro:
    menu bar "MIDI" -> "DualSense MIDI" -> "Configure..." -> MIDI Learn
    NOTE: MIDI mapping requires a djay PRO subscription.
    NOTE: start this bridge BEFORE launching djay, or restart djay.
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

# Names reported by SDL/IOKit for a PS5 pad (and a PS4 pad, which is
# intentionally accepted too since it uses the same layout).
CONTROLLER_HINTS = ("DualSense", "PS5", "DualShock", "Wireless Controller")

# ------------------------------------------------------------------ defaults
# buttons: raw SDL button index -> MIDI note number / label
# axes   : raw SDL axis index   -> MIDI CC number / label
DEFAULT_MAPPING = {
    "midi_port_name": "DualSense MIDI",
    "channel": 0,
    "deadzone": 0.08,
    "buttons": {
        "0":  {"note": 38, "label": "Square"},
        "1":  {"note": 36, "label": "Cross"},
        "2":  {"note": 37, "label": "Circle"},
        "3":  {"note": 39, "label": "Triangle"},
        "4":  {"note": 44, "label": "L1"},
        "5":  {"note": 45, "label": "R1"},
        "6":  {"note": 46, "label": "L2 (digital)"},
        "7":  {"note": 47, "label": "R2 (digital)"},
        "8":  {"note": 48, "label": "Create"},
        "9":  {"note": 49, "label": "Options"},
        "10": {"note": 50, "label": "L3"},
        "11": {"note": 51, "label": "R3"},
        "12": {"note": 52, "label": "PS (hold = power off)"},
        "13": {"note": 53, "label": "Mic mute"},
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
    """Load mapping.json, creating it from the defaults on first run."""
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
    """Convert a -1.0 .. 1.0 axis value to 0..127."""
    if invert:
        v = -v
    n = int(round((v + 1.0) / 2.0 * 127))
    return max(0, min(127, n))


def open_controller(rescan: bool = False):
    """Return the first joystick that looks like a PlayStation pad.

    SDL only notices hot-plugged devices while events are being pumped, and
    it caches the joystick list. A controller that briefly drops out (sleep,
    Bluetooth hiccup) is therefore never seen again unless we tear the
    subsystem down and re-enumerate it.
    """
    if rescan:
        pygame.joystick.quit()
    pygame.joystick.init()
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        name = j.get_name()
        if any(h.lower() in name.lower() for h in CONTROLLER_HINTS):
            return j
    return None


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
        # Parent PID 1 means launchd owns us, so exiting is safe: KeepAlive
        # brings us straight back with a clean SDL.
        self.under_launchd = (os.getppid() == 1)

    # ------------------------------------------------------------- MIDI out
    def note(self, number: int, on: bool, velocity: int = 100):
        status = 0x90 if on else 0x80
        self.midi.send_message([status | self.channel, number, velocity if on else 0])

    def cc(self, number: int, value: int):
        self.midi.send_message([0xB0 | self.channel, number, value])

    # ---------------------------------------------------------------- input
    def run(self):
        print(f"[OK] Virtual MIDI port created: {self.port_name}", flush=True)
        # A long-lived SDL process can permanently lose sight of a gamepad
        # that dropped out: even joystick.quit()/init() will not bring it
        # back. Two escalating recovery steps:
        #   1. every few misses -> fully re-initialise SDL
        #   2. still nothing   -> exit so launchd (KeepAlive) restarts us,
        #                         which always sees the device again
        misses = 0
        while self.running:
            # Must happen on every iteration, including the "searching" path:
            # SDL only picks up hot-plugged devices while events are pumped.
            try:
                pygame.event.pump()
            except Exception:
                pass

            if self.joy is None:
                self.joy = open_controller(rescan=True)
                if self.joy is None:
                    misses += 1
                    print("[..] Looking for a DualSense... "
                          "(hold PS + Create to pair)", flush=True)
                    if misses % 4 == 0:
                        print("[..] re-initialising SDL...", flush=True)
                        try:
                            pygame.quit()
                        except Exception:
                            pass
                        pygame.init()
                        pygame.joystick.init()
                    # Don't linger: every second spent here is a second the
                    # MIDI port is missing from the app's point of view.
                    if self.under_launchd and misses >= 8:
                        print("[!!] not recoverable in this process - "
                              "exiting so launchd restarts me", flush=True)
                        self.close()
                        sys.exit(3)
                    time.sleep(1.0)
                    continue
                misses = 0
                print(f"[OK] Connected: {self.joy.get_name()} "
                      f"(axes={self.joy.get_numaxes()}, "
                      f"buttons={self.joy.get_numbuttons()})")
                self.last_axis.clear()
                self.last_btn.clear()
                for _ in range(5):
                    pygame.event.pump()
                    time.sleep(0.05)
                for a in range(self.joy.get_numaxes()):
                    self.emit_axis(a)

            for ev in pygame.event.get():
                if ev.type == pygame.JOYDEVICEREMOVED:
                    self.drop("disconnected")
            if self.joy is not None:
                self.poll()
            time.sleep(0.005)

    def drop(self, why: str = ""):
        """Forget the current joystick so the next iteration re-scans."""
        if self.joy is not None:
            suffix = f" ({why})" if why else ""
            print(f"[!!] Controller lost{suffix} - reconnecting...", flush=True)
        self.joy = None

    def poll(self):
        """Read state every frame instead of trusting events alone."""
        j = self.joy
        try:
            nb = j.get_numbuttons()
            na = j.get_numaxes()
        except Exception:
            self.drop("read error")
            return
        for b in range(nb):
            try:
                v = j.get_button(b)
            except Exception:
                self.drop("button read error")
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
            print(f"    axis {idx:>2} -> CC {int(m['cc']):<3} = {val:<4} "
                  f"{m.get('label','')}", flush=True)

    def close(self):
        self.running = False
        try:
            # Release only the notes this mapping can actually produce.
            for m in self.bmap.values():
                self.note(int(m["note"]), False)
            self.midi.close_port()
        except Exception:
            pass
        pygame.quit()


def probe():
    """Print the raw button/axis numbers as you press them."""
    pygame.init()
    pygame.joystick.init()
    j = open_controller()
    if j is None:
        print("No PlayStation controller found. Pair it first "
              "(hold PS + Create) and try again.")
        return
    print(f"Found: {j.get_name()} "
          f"axes={j.get_numaxes()} buttons={j.get_numbuttons()}")
    print("Press buttons / move sticks and triggers. Ctrl+C to quit.\n")
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
        print("\nBye")
    pygame.quit()


def list_ports():
    mo = rtmidi.MidiOut()
    print("Available MIDI destinations:")
    for i, p in enumerate(mo.get_ports()):
        print(f"  [{i}] {p}")
    print("\n(A virtual port becomes visible to other apps after it is created.)")


def main():
    ap = argparse.ArgumentParser(
        description="Turn a PS5 DualSense into a MIDI controller on macOS.")
    ap.add_argument("--probe", action="store_true",
                    help="print raw button/axis numbers")
    ap.add_argument("--ports", action="store_true",
                    help="list MIDI destinations")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress input logging")
    ap.add_argument("--test", action="store_true",
                    help="send a test pattern, then keep running")
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
        print("[test] Sending Note 36-39 on/off and a CC 1 sweep")
        for n in (36, 37, 38, 39):
            b.note(n, True)
            time.sleep(0.4)
            b.note(n, False)
            time.sleep(0.1)
        for v in (0, 64, 127, 64, 0):
            b.cc(1, v)
            time.sleep(0.3)
        print("[test] Done")

    def handler(signum, frame):
        b.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    print(f"[..] Using mapping from {CONFIG_PATH}")
    print(f"[..] In djay Pro: menu bar \"MIDI\" -> "
          f"\"{cfg.get('midi_port_name')}\" -> \"Configure...\"")
    print("[..] Ctrl+C to quit\n")
    b.run()


if __name__ == "__main__":
    main()
