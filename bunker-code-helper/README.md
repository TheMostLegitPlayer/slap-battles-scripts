# Bunker Code Helper

Solves the Slap Battles **bunker-code** board: press a hotkey → it screenshots the screen,
reads/solves the math task panels, and shows the joined code in a small overlay box at the
top. Works on Windows and Linux.

> ⚠ Automating or assisting in a game can break its rules and get an account **banned**.
> Use a throwaway account, for yourself only, entirely at your **own risk**. Not for
> harassment or any malicious use.

## Setup

1. Install [Python 3.10+](https://www.python.org/downloads/) (tick **Add to PATH**).
2. Open the settings window:
   - **Windows:** double-click **`setup.bat`**
   - **Linux:** `bash linux/setup.sh`
3. Pick a provider, paste your **API key**, press **Save**.

Get a free key from **[Google AI Studio](https://aistudio.google.com/apikey)** (Gemini,
recommended). Other OpenAI-compatible providers and a fully-local option are available in
the preset buttons too.

Your API key is stored locally in `app/config/settings.json` and is **never committed**.

## Run

- **Windows:** double-click **`run.bat`**
- **Linux:** `bash linux/run.sh`

Then press the hotkey (default **End**) in-game — the answer appears in the overlay.
Press **F8** to quit. Re-run setup any time to change settings.
