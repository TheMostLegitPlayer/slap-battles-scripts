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
bash farmbot/run.sh      # makes a .venv, installs deps, runs
```
Linux input goes through pynput (XTEST) — no root needed — and window detection uses
`xdotool` (`sudo apt install xdotool`).

See each folder for its own hotkeys and notes.
