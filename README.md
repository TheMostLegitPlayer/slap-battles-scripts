# Slap Battles Scripts

Personal helper scripts for the Roblox game **Slap Battles**. One folder per script.

> ⚠ Automating a game is against Roblox rules and can get an account **banned**. Use a
> throwaway account, for yourself only, at your **own risk**. Not for harassment or any
> malicious use.

## Scripts

| Folder | What it does |
|---|---|
| [`farmbot/`](farmbot/) | Auto-farm loop. Cross-platform (Windows + Linux/Sober). |
| [`bunker-code-helper/`](bunker-code-helper/) | Solves the bunker-code board: hotkey → screenshot → AI → overlay code. Needs an API key (see its README). Windows + Linux. |

_(more coming)_

## Run

**Windows:** double-click the script's `run.bat`.

**Linux (Roblox via Sober):**
```bash
sudo apt install xdotool ydotool     # one-time
bash farmbot/run.sh                   # makes a .venv, installs deps, runs
```
Hotkeys and any extra notes are inside each folder's script. `bunker-code-helper/`
has its own setup step (pick a provider + paste an API key) — run
`bash bunker-code-helper/linux/setup.sh` once, then `bash bunker-code-helper/linux/run.sh`.
