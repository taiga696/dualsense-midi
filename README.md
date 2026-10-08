# DualSense MIDI

**Turn a PS5 DualSense controller into a real MIDI controller on macOS.**

[日本語版 README / Japanese version](README.ja.md)

A DualSense is an **HID gamepad**. It speaks HID, not MIDI — which is exactly why
pairing it over Bluetooth never makes it appear in djay, Ableton, Logic or any
other MIDI app. That is not a bug or a settings problem; it is simply a different
protocol.

This project puts a tiny translation layer in between. It reads the gamepad and
re-emits every input as MIDI on a **Core MIDI virtual port**, so any app sees it
as an ordinary MIDI controller.

```
DualSense ──(Bluetooth / USB)──▶ dualsense_midi.py ──(Core MIDI)──▶ virtual port "DualSense MIDI" ──▶ your app
```

No IAC Driver configuration is needed — the virtual port is created in-process,
so it exists only while the script is running.

---

## Requirements

- macOS 11 or later (Apple Silicon and Intel)
- A DualSense (PS5) controller — Bluetooth or USB
- Python 3.9+
- Any app that accepts MIDI input (djay Pro, Ableton Live, Logic Pro, ...)

> **djay Pro users:** MIDI mapping requires a **PRO subscription**. This is stated
> in Algoriddim's own documentation, and without it the mapping screen never
> opens: https://help.algoriddim.com/user-manual/djay-pro-mac/midi/mapping

---

## Install

```bash
git clone https://github.com/taiga696/dualsense-midi.git ~/DualSenseMIDI
cd ~/DualSenseMIDI

python3 -m venv ~/.dualsense-midi-venv
source ~/.dualsense-midi-venv/bin/activate
pip install -r requirements.txt
```

Dependencies: `pygame` (reads the gamepad via SDL) and `python-rtmidi` (sends MIDI).

---

## Usage

```bash
python3 dualsense_midi.py            # run the bridge
python3 dualsense_midi.py --probe    # print raw button / axis numbers
python3 dualsense_midi.py --ports    # list MIDI destinations
python3 dualsense_midi.py --test     # send a test pattern
python3 dualsense_midi.py --quiet    # run without input logging
```

On success you will see:

```
[OK] Virtual MIDI port created: DualSense MIDI
[OK] Connected: DualSense Wireless Controller (axes=6, buttons=17)
```

The Mac now has a MIDI device called **"DualSense MIDI"**. Pick it from your app's
MIDI input list.

### Start order matters

Most apps (including djay) scan for MIDI devices **once at launch**. So:

1. Start this bridge **first**
2. Then launch your app

If your app is already running, restart it. `dj.command` below handles this for you.

### Wired or wireless?

Both work. **Wired (USB-C) is the more stable of the two**, and it is what we
recommend if your Mac is close enough:

| | USB (wired) | Bluetooth |
|---|---|---|
| Setup | plug the cable in | pair once with PS + Create |
| Sleep disconnects | none | yes — the controller sleeps when idle |
| PS button risk | harmless | long-press drops the link |
| Latency | lowest | fine for DJ use (~5 ms polling) |

Plugging the cable in makes macOS switch the controller off Bluetooth by itself,
so seeing **"Not Connected"** on the Bluetooth side afterwards is normal — not a
fault. The controller charges at the same time.

Either way, restart the bridge (or just unplug/replug) after switching, then
restart your app so it rescans.

### Helper scripts (macOS)

| Script | What it does |
|---|---|
| `dj.command` | starts the bridge, checks the controller (USB or Bluetooth), then launches/restarts djay Pro |
| `start.command` | starts the bridge only (double-clickable) |
| `stop.command` | stops the bridge |
| `button_probe.command` | prints raw button / axis numbers |
| `install_service.command` | installs the bridge as a LaunchAgent (auto-start at login, auto-restart on crash) |
| `uninstall_service.command` | removes the LaunchAgent |
| `status.command` | health check: bridge, LaunchAgent, MIDI port, USB/Bluetooth link, and how many times it has restarted |

### Optional: run it automatically at login

```bash
cd ~/DualSenseMIDI
./install_service.command
```

This registers a LaunchAgent (`~/Library/LaunchAgents/com.dualsense.midi.plist`) with
`RunAtLoad` and `KeepAlive`, so the MIDI port is always up before you open your DJ app —
no more start-order problems. Logs go to `bridge.log`. Remove it with
`uninstall_service.command`.

Run it from a normal Terminal window (`launchctl` needs your GUI session). If you
prefer a GUI route instead: System Settings → General → Login Items → add `start.command`.

Add an alias if you like:

```bash
alias dj="$HOME/DualSenseMIDI/dj.command"
```

### Setting up djay Pro

1. Restart djay Pro
2. Menu bar **MIDI → "DualSense MIDI" → Configure...**
3. Press a button on the controller — it is detected automatically
4. Assign a **Target** (what to control) and an **Action** (what to do)
5. Press **Done**

---

## Default mapping

Edit `mapping.json` and restart to change it.

### Buttons → MIDI note

| Button | Note | | Button | Note |
|---|---|---|---|---|
| □ Square | 38 | | Create | 48 |
| ✕ Cross | 36 | | Options | 49 |
| ○ Circle | 37 | | L3 | 50 |
| △ Triangle | 39 | | R3 | 51 |
| L1 | 44 | | PS | 52 |
| R1 | 45 | | Mic mute | 53 |
| L2 (digital) | 46 | | Touchpad | 54 |
| R2 (digital) | 47 | | | |

### Sticks / triggers → MIDI CC (continuous)

| Input | CC | | Input | CC |
|---|---|---|---|---|
| Left stick X / Y | 7 / 8 | | L2 trigger | 1 |
| Right stick X / Y | 10 / 11 | | R2 trigger | 2 |

Stick Y axes are inverted by default (up = 127). L2/R2 send **both** a continuous
CC and a digital note when fully pressed.

> Button order can vary by OS / SDL version. If something feels off, run
> `--probe` and compare the printed numbers with `mapping.json`.

> ⚠️ **Be careful with the PS button.** A quick tap is fine, but holding it for
> about a second powers the controller off (or puts it into pairing mode). That
> drops the Bluetooth connection, and with it the MIDI port — your app will
> lose the device until it is restarted. If you need one more button, use
> R1 (note 45) instead.

### Example: a working djay layout

Two-deck layout, verified on djay Pro. Note names as djay displays them
(C3 = 48 in djay's numbering).

**Deck 1**

| Button | MIDI | Action |
|---|---|---|
| Options | Note C#3 (49) | Play / Pause |
| L2 trigger | CC 1 | Cue |
| R2 | Note B2 (47) | Set Start Cue |
| L1 | Note G#2 (44) | Loop In/Out |
| R3 | Note D#3 (51) | Tempo + |
| PS | Note E3 (52) | Tempo − |
| Touchpad | Note F#3 (54) | Pitch Bend + |
| Mic mute | Note F3 (53) | Pitch Bend − |
| Left stick Y | CC 8 | Filter |

**Deck 2**

| Button | MIDI | Action |
|---|---|---|
| L3 | Note D3 (50) | Play / Pause |
| R2 trigger | CC 2 | Cue |
| Create | Note C3 (48) | Set Start Cue |
| L2 | Note A#2 (46) | Loop In/Out |
| △ | Note D#2 (39) | Tempo + |
| □ | Note D2 (38) | Tempo − |
| ✕ | Note C2 (36) | Pitch Bend + |
| ○ | Note C#2 (37) | Pitch Bend − |
| Right stick Y | CC 11 | Filter |

> ⚠️ **PS = Tempo −** works, but if you hold it slightly too long the controller
> powers off and the connection drops. If your setup keeps cutting out, move
> that one action to R1 (Note 45) and leave the PS button alone.

Tempo is on **buttons**, not sticks: a stick snaps back to center when released,
which would make the tempo jump. Filter on a stick is the opposite — it returns to
neutral on its own, which feels good.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "DualSense MIDI" does not appear | bridge not running, or started after the app | start the bridge first, restart the app |
| Mapping screen will not open (djay) | no PRO subscription | djay Pro subscription required |
| Buttons do nothing | button indices differ | run `--probe`, fix `mapping.json` |
| Controller not detected | Bluetooth pairing lost, or USB cable not seated | hold **PS + Create** to re-pair, or plug the USB-C cable in |
| Cable plugged in but nothing changes | charge-only cable, or hub in between | use the cable that came with the console, plug straight into the Mac |
| Parameters drift on their own | gyro/accelerometer noise | this bridge ignores motion sensors |

To check what the Mac actually sees:

```bash
ioreg -p IOUSB -w0 -l | grep -i DualSense   # wired
```

Latency over Bluetooth is not noticeable for DJ use: polling runs at 200 Hz
(5 ms) and the MIDI travels inside the Mac's own Core MIDI, with no external
audio buffer involved. Wired is a little snappier still.

---

## How it works

- Input: `pygame` (SDL 2.x) reads the gamepad
- Output: `python-rtmidi` opens a virtual port (Core MIDI `MIDIDestinationCreate`)
- Polling: every 5 ms, state is read directly rather than relying only on events,
  so no input is dropped
- No IAC Driver setup, no third-party app, no kernel extension

`midi_monitor.py` is included if you want to watch the raw messages:

```bash
python3 midi_monitor.py 15
```

---

## Limitations

- **macOS only.** On Windows the same idea works with `GameControllers2MIDI`
  plus `loopMIDI`, but that is untested here.
- **No jog wheel.** Scratching does not feel right.
- Only enough controls for a minimal 2-deck setup.
- The PS button may trigger macOS system UI depending on your settings (it still
  sends MIDI).
- iOS/iPadOS is not supported — there is no gamepad→MIDI layer there.
- For real gigs, buy a proper controller. For learning what MIDI actually does
  with hardware you already own, this is hard to beat.

---

## License

MIT. See [LICENSE](LICENSE).
