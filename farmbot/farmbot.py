"""
farmbot.py — cross-platform Slap Battles farm loop (Windows + Linux/Sober).

  F7  — start/stop the farm loop
  F8  — start/stop walk-only
  F5  — reset (Esc R Enter)
  F6  — test-click "Go To Portal"
  F10 — quit

Loop: click Go To Portal -> find direction from the screen -> walk 0.5s -> E,E
-> reset -> repeat.

Input (keys/mouse/hotkeys) goes through pynput, so it works the same on Windows
and on Linux/X11 (Roblox via Sober). Window detection is per-OS: EnumWindows on
Windows, `xdotool` on Linux. Screen capture uses mss.

⚠ Automation is against Roblox rules — use a throwaway account, at your own risk.
"""
import os
import time
import shutil
import platform
import subprocess
from collections import namedtuple

import numpy as np
import mss
from pynput import keyboard as _kb, mouse as _ms

_MSS = getattr(mss, "MSS", None) or mss.mss     # new API, fall back to old alias
IS_WIN = platform.system() == "Windows"
Rect = namedtuple("Rect", "left top right bottom")

# ---- tuning (screen-relative, resolution independent) ----------------------
ROI_TOP, ROI_BOT = 0.13, 0.33      # band to look for the dark ceiling wedge
DARK_V = 60                        # "dark" threshold per channel
MIN_DARK = 200                     # min dark pixels to trust a detection
TIP_BAND = 12                      # rows near the wedge tip to average
DEAD_FRAC = 0.07                   # centre dead-zone -> walk backwards (S)
GO_BTN = (0.50, 0.925)             # "Go To Portal" button, relative to window
AFTER_RESET = 4.5                  # seconds to wait after a reset

# ---- input --------------------------------------------------------------
# Mouse goes through pynput on both OSes (works in Sober). Keyboard differs:
# on Windows pynput is fine, but on Linux/Sober synthetic XTEST keys are ignored
# by Roblox, so we inject real key events via ydotool (uinput, kernel level).
_mouse = _ms.Controller()

if IS_WIN:
    _kbd = _kb.Controller()
    _KEYMAP = {"W": "w", "A": "a", "S": "s", "D": "d", "R": "r", "E": "e",
               "ESC": _kb.Key.esc, "ENTER": _kb.Key.enter}

    def kdown(n):
        _kbd.press(_KEYMAP[n])

    def kup(n):
        _kbd.release(_KEYMAP[n])

    def tap(n, d):
        kdown(n)
        time.sleep(d)
        kup(n)

    def release_all():
        for k in ("W", "A", "S", "D"):
            try:
                kup(k)
            except Exception:
                pass

else:
    # Linux input-event keycodes (linux/input-event-codes.h)
    _YKEY = {"W": 17, "A": 30, "S": 31, "D": 32, "R": 19, "E": 18,
             "ESC": 1, "ENTER": 28}

    def tap(n, d):
        # one ydotool call = one uinput device lifetime: press, hold, release.
        # (0.1.8 has no daemon, so a key can't be held across two processes.)
        # keep ydotool's default start --delay (~100ms): it lets the freshly
        # created uinput device settle, otherwise the key event gets dropped.
        hold = max(1, int(d * 1000))
        subprocess.run(["ydotool", "key", "--key-delay", str(hold),
                        f"{_YKEY[n]}:1", f"{_YKEY[n]}:0"], capture_output=True)

    def release_all():
        pass                        # ydotool taps never leave a key held


def click(x, y):
    _mouse.position = (int(x), int(y))
    time.sleep(0.08)
    _mouse.press(_ms.Button.left)
    time.sleep(0.10)
    _mouse.release(_ms.Button.left)


def abspos(rect, rel):
    w, h = rect.right - rect.left, rect.bottom - rect.top
    return rect.left + w * rel[0], rect.top + h * rel[1]


# ---- window detection / focus (per-OS) -------------------------------------
if IS_WIN:
    import ctypes
    from ctypes import wintypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    _u = ctypes.WinDLL("user32", use_last_error=True)
    TARGET_PROC = "robloxplayerbeta.exe"

    def find_window():
        out = []
        EP = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        k32 = ctypes.WinDLL("kernel32")

        def cb(h, _l):
            if _u.IsWindowVisible(h):
                pid = wintypes.DWORD()
                _u.GetWindowThreadProcessId(h, ctypes.byref(pid))
                hp = k32.OpenProcess(0x1000, False, pid.value)
                if hp:
                    buf = ctypes.create_unicode_buffer(260)
                    sz = wintypes.DWORD(260)
                    k32.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(sz))
                    k32.CloseHandle(hp)
                    if buf.value.lower().endswith(TARGET_PROC):
                        t = ctypes.create_unicode_buffer(256)
                        _u.GetWindowTextW(h, t, 256)
                        r = wintypes.RECT()
                        _u.GetWindowRect(h, ctypes.byref(r))
                        if (r.right - r.left) > 300 and (r.bottom - r.top) > 300:
                            out.append((h, Rect(r.left, r.top, r.right, r.bottom),
                                        (r.right-r.left)*(r.bottom-r.top), t.value))
            return True
        _u.EnumWindows(EP(cb), 0)
        if not out:
            return None, None
        named = [o for o in out if o[3] == "Roblox"] or out
        named.sort(key=lambda o: o[2], reverse=True)
        return named[0][0], named[0][1]

    def focus(h):
        _u.ShowWindow(h, 9)
        fg = _u.GetForegroundWindow()
        t1 = _u.GetWindowThreadProcessId(fg, None)
        t2 = _u.GetWindowThreadProcessId(h, None)
        _u.AttachThreadInput(t1, t2, True)
        _u.SetForegroundWindow(h)
        _u.AttachThreadInput(t1, t2, False)
        time.sleep(0.3)

else:   # ---- Linux (X11) via xdotool ----
    def _xdo(*args):
        try:
            return subprocess.run(["xdotool", *args], capture_output=True, text=True)
        except FileNotFoundError:
            print("[!] xdotool not installed:  sudo apt install xdotool", flush=True)
            raise SystemExit(1)

    # Sober/Roblox window can show up under a few names/classes — try them all.
    _QUERIES = (["search", "--name", "Roblox"],
                ["search", "--class", "sober"],
                ["search", "--name", "Sober"],
                ["search", "--classname", "sober"])

    def find_window():
        ids = []
        for q in _QUERIES:
            r = _xdo(*q)
            if r.returncode == 0:
                ids += [i for i in r.stdout.split() if i]
        best, barea = (None, None), 0
        for wid in dict.fromkeys(ids):                 # dedupe, keep order
            g = _xdo("getwindowgeometry", "--shell", wid)
            if g.returncode != 0:
                continue
            d = {}
            for line in g.stdout.splitlines():
                if "=" in line:
                    kk, _, vv = line.partition("=")
                    d[kk] = vv
            try:
                x, y = int(d["X"]), int(d["Y"])
                w, h = int(d["WIDTH"]), int(d["HEIGHT"])
            except Exception:
                continue
            if w > 300 and h > 300 and w * h > barea:
                barea, best = w * h, (wid, Rect(x, y, x + w, y + h))
        return best

    def focus(wid):
        _xdo("windowactivate", "--sync", wid)
        time.sleep(0.3)


# ---- screen capture + portal detection (pure numpy) ------------------------
def grab(sct, rect):
    mon = {"left": rect.left, "top": rect.top,
           "width": rect.right - rect.left, "height": rect.bottom - rect.top}
    return np.array(sct.grab(mon))[:, :, :3]           # BGRA -> BGR


def detect_portal(bgr):
    h, w = bgr.shape[:2]
    y0, y1 = int(h * ROI_TOP), int(h * ROI_BOT)
    roi = bgr[y0:y1, :]
    b, g, r = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
    mask = (b < DARK_V) & (g < DARK_V) & (r < DARK_V)
    mask[:, :int(w * 0.12)] = False
    mask[:, int(w * 0.96):] = False
    ys, xs = np.nonzero(mask)
    if ys.size < MIN_DARK:
        return "S", None
    ymax = ys.max()
    tipx = xs[ys >= ymax - TIP_BAND]
    if tipx.size == 0:
        return "S", None
    cx = float(np.median(tipx))
    if abs(cx - w / 2) < w * DEAD_FRAC:
        return "S", cx                                 # centre = behind -> back
    return ("A" if cx < w / 2 else "D"), cx


# ---- farm loop -------------------------------------------------------------
run_farm = run_walk = False
alive = True
_hwnd = _rect = None


def do_reset():
    print("  [reset] Esc R Enter", flush=True)
    tap("ESC", 0.05); time.sleep(0.18)
    tap("R", 0.05); time.sleep(0.08)
    tap("ENTER", 0.05); time.sleep(0.08)


def walk_once(sct, rect):
    d, cx = detect_portal(grab(sct, rect))
    cxs = f"{cx:.0f}" if cx is not None else "-"
    print(f"  found: {d} (cx={cxs}), walking 0.5s", flush=True)
    release_all(); tap(d, 0.5); release_all()


def ensure_front():
    """Find the live Roblox window and bring it forward. False if the game is
    gone (then we DON'T act, so the bot never 'farms the desktop')."""
    global _hwnd, _rect, run_farm, run_walk
    found = find_window()
    if not found or not found[0]:
        print("[!] Roblox window not found — stopping (game closed?)", flush=True)
        release_all()
        run_farm = run_walk = False
        return False
    _hwnd, _rect = found
    focus(_hwnd)
    return True


def farm_cycle(sct):
    if not ensure_front():
        time.sleep(1.0)
        return
    rect = _rect
    print("  click Go To Portal", flush=True)
    click(*abspos(rect, GO_BTN)); time.sleep(0.5)
    if not run_farm:
        return
    walk_once(sct, rect)
    time.sleep(0.3)
    print("  E", flush=True)
    tap("E", 0.15); time.sleep(0.15)
    tap("E", 0.15); time.sleep(0.3)
    do_reset()
    time.sleep(AFTER_RESET)


# ---- hotkeys (pynput; works on Windows + Linux/X11) ------------------------
def _toggle_farm():
    global run_farm
    run_farm = not run_farm
    print(f"[i] FARM: {'ON' if run_farm else 'off'}", flush=True)
    if not run_farm:
        release_all()


def _toggle_walk():
    global run_walk
    run_walk = not run_walk
    print(f"[i] walk: {'ON' if run_walk else 'off'}", flush=True)
    if not run_walk:
        release_all()


def _test_click():
    if ensure_front():
        click(*abspos(_rect, GO_BTN))


def _quit():
    global alive
    release_all()
    print("quit", flush=True)
    alive = False


def main():
    global _rect, _hwnd
    if not IS_WIN:
        print("[i] Linux: mouse/hotkeys via pynput (X11), keys via ydotool (uinput).")
        if not shutil.which("ydotool"):
            print("[!] ydotool not found — movement keys won't reach the game.\n"
                  "    Install:  sudo apt install ydotool")
        elif not os.access("/dev/uinput", os.W_OK):
            print("[!] /dev/uinput not writable — ydotool keys will fail.\n"
                  "    Fix:  sudo chgrp input /dev/uinput && sudo chmod 660 /dev/uinput\n"
                  "    (you're in group 'input'); a reboot-safe udev rule may be needed.")
    found = find_window()
    if not found or not found[0]:
        print("[!] Roblox window not found. Launch the game and try again.")
        time.sleep(3)
        return
    _hwnd, _rect = found
    print(f"[i] Roblox window {_rect.right-_rect.left}x{_rect.bottom-_rect.top}")
    print("  F7 farm | F8 walk | F5 reset | F6 test-click | F10 quit", flush=True)

    hk = _kb.GlobalHotKeys({"<f7>": _toggle_farm, "<f8>": _toggle_walk,
                            "<f5>": do_reset, "<f6>": _test_click,
                            "<f10>": _quit})
    hk.start()

    with _MSS() as sct:
        while alive:
            if run_farm:
                farm_cycle(sct)
            elif run_walk:
                if ensure_front():
                    walk_once(sct, _rect)
                else:
                    time.sleep(0.5)
            else:
                time.sleep(0.03)
    hk.stop()


if __name__ == "__main__":
    main()
