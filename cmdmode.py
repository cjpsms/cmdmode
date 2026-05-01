#!/usr/bin/env python3
"""
cmdmode — triple Super tap → type a command → run it instantly
"""

import evdev
import json
import os
import select
import subprocess
import sys
import time
from evdev import ecodes as e

CONFIG_PATH = os.path.expanduser("~/.config/cmdmode/commands.json")
TRIPLE_TAP_MS = 600   # ms window for 3 taps to count
CMD_TIMEOUT_S = 5     # seconds before command mode auto-cancels

KEY_TO_CHAR = {
    e.KEY_A: 'a', e.KEY_B: 'b', e.KEY_C: 'c', e.KEY_D: 'd', e.KEY_E: 'e',
    e.KEY_F: 'f', e.KEY_G: 'g', e.KEY_H: 'h', e.KEY_I: 'i', e.KEY_J: 'j',
    e.KEY_K: 'k', e.KEY_L: 'l', e.KEY_M: 'm', e.KEY_N: 'n', e.KEY_O: 'o',
    e.KEY_P: 'p', e.KEY_Q: 'q', e.KEY_R: 'r', e.KEY_S: 's', e.KEY_T: 't',
    e.KEY_U: 'u', e.KEY_V: 'v', e.KEY_W: 'w', e.KEY_X: 'x', e.KEY_Y: 'y',
    e.KEY_Z: 'z',
}


def find_keyboards():
    devices = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
            caps = dev.capabilities()
            keys = caps.get(e.EV_KEY, [])
            if e.KEY_A in keys and e.KEY_LEFTMETA in keys:
                devices.append(dev)
        except Exception:
            pass
    return devices


def load_commands():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def notify(msg, urgency="normal"):
    subprocess.Popen(
        ["notify-send", "-u", urgency, "-t", "2000", "-a", "cmdmode", msg],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def run_command(cmd):
    cmd = os.path.expanduser(cmd)
    subprocess.Popen(cmd, shell=True)


def has_prefix(commands, buf):
    return any(k.startswith(buf) for k in commands)


def command_mode(device, commands):
    notify("▸ ", urgency="low")
    buf = ""
    device.grab()
    try:
        while True:
            r, _, _ = select.select([device.fd], [], [], CMD_TIMEOUT_S)
            if not r:
                notify("✗ timeout", urgency="low")
                return

            for event in device.read():
                if event.type != e.EV_KEY or event.value != 1:
                    continue

                if event.code == e.KEY_ESC:
                    return

                if event.code == e.KEY_BACKSPACE:
                    buf = buf[:-1]
                    continue

                if event.code in KEY_TO_CHAR:
                    buf += KEY_TO_CHAR[event.code]

                    if buf in commands:
                        run_command(commands[buf])
                        notify(f"→ {buf}")
                        return

                    if not has_prefix(commands, buf):
                        notify(f"✗ {buf}", urgency="critical")
                        return
    finally:
        try:
            device.ungrab()
        except Exception:
            pass


def main():
    keyboards = find_keyboards()
    if not keyboards:
        print("No keyboard with Super key found.", file=sys.stderr)
        print("Make sure you're in the 'input' group: sudo usermod -aG input $USER", file=sys.stderr)
        sys.exit(1)

    print(f"Monitoring {len(keyboards)} keyboard(s):")
    for kb in keyboards:
        print(f"  {kb.path}: {kb.name}")

    fds = {kb.fd: kb for kb in keyboards}
    super_times = []   # tracks timestamps of Super keydown events

    while True:
        r, _, _ = select.select(fds.keys(), [], [], 1.0)
        for fd in r:
            device = fds[fd]
            try:
                events = device.read()
            except Exception:
                continue

            for event in events:
                if event.type != e.EV_KEY:
                    continue
                if event.code not in (e.KEY_LEFTMETA, e.KEY_RIGHTMETA):
                    continue
                if event.value != 1:  # keydown only
                    continue

                now = time.monotonic()
                super_times = [t for t in super_times if now - t < TRIPLE_TAP_MS / 1000]
                super_times.append(now)

                if len(super_times) >= 3:
                    super_times = []
                    try:
                        commands = load_commands()
                    except Exception as ex:
                        notify(f"config error: {ex}", urgency="critical")
                        continue
                    command_mode(device, commands)


if __name__ == "__main__":
    main()
