# Slap Battles Scripts

A small collection of personal helper scripts for the Roblox game **Slap Battles**.
One folder per script.

> ⚠ Automating a game is against Roblox rules and can get an account **banned**. Use a
> throwaway account, only for yourself, at your **own risk**. Not for harassment or any
> malicious use.

## Scripts

| Folder | What it does |
|---|---|
| [`farmbot/`](farmbot/) | Auto-farm loop: click *Go To Portal* → walk toward the portal (screen-read) → interact → reset → repeat. Cross-platform (Windows + Linux/Sober). |

_(more coming: fishing helper, farm + auto-click opponents)_

## Run

**Windows:** double-click the script's `run.bat`.

**Linux (X11 / Roblox via Sober):**
```bash
sudo apt install xdotool ydotool     # one-time
bash farmbot/run.sh                   # makes a .venv, installs deps, runs
```
On Linux: mouse + hotkeys go through pynput (XTEST, no root); **movement keys go through
`ydotool`** (uinput) because Sober/Wine ignores synthetic XTEST key presses; window
detection uses `xdotool`. `ydotool` needs write access to `/dev/uinput` — add yourself to
the `input` group and make the device group-writable (a udev rule keeps it across reboots):
```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo usermod -aG input "$USER"        # then re-login
```

See each folder for its own hotkeys and notes.
