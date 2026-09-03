"""
Bunker Code Helper - Setup
===========================
A friendly config window: pick Gemini or OpenAI, paste your API key, choose the
screenshot hotkey, tweak the prompt, then Save & create run.bat.

Run it with setup.bat (which installs customtkinter if needed).
"""
import os
import sys
import json

APP = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(APP, "config")
ROOT = os.path.dirname(APP)
os.makedirs(CFG, exist_ok=True)

try:
    import customtkinter as ctk
except ImportError:
    import tkinter.messagebox as mb
    mb.showerror("Missing library",
                 "customtkinter isn't installed.\n\nRun setup.bat first, or:\n"
                 "   pip install customtkinter")
    sys.exit(1)

DEFAULT_PROMPT = ""      # extra notes are empty by default (built-in prompt is used)
MODEL_HINT = {"gemini": "gemini-3.5-flash-lite", "openai": "gpt-4o-mini"}

# One-click presets. gemini uses the native API (no base_url); the rest are all
# OpenAI-compatible — same code path, just a different base_url. Model ids are
# suggestions; edit the Model field if a provider renames them.
# (provider, base_url, suggested_model)
PRESETS = {
    "Gemini (free)":  ("gemini", "", "gemini-3.5-flash-lite"),
    "Ollama (local)": ("openai", "http://localhost:11434/v1", "qwen2.5vl:7b"),
    "OpenAI":         ("openai", "https://api.openai.com/v1", "gpt-4o-mini"),
    "NVIDIA NIM (free)": ("openai", "https://integrate.api.nvidia.com/v1",
                          "meta/llama-3.2-90b-vision-instruct"),
    "Groq (free)":    ("openai", "https://api.groq.com/openai/v1",
                       "meta-llama/llama-4-scout-17b-16e-instruct"),
    "Mistral (free)": ("openai", "https://api.mistral.ai/v1", "pixtral-12b-2409"),
    "OpenRouter":     ("openai", "https://openrouter.ai/api/v1",
                       "meta-llama/llama-3.2-11b-vision-instruct:free"),
}


def load():
    try:
        with open(os.path.join(CFG, "settings.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


s = load()

# single instance
import socket
_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    _lock.bind(("127.0.0.1", 50581))
    _lock.listen(1)
except OSError:
    sys.exit(0)

# ---------------------------------------------------------------- UI
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
ACCENT = "#7264ff"
OK = "#00c46a"

root = ctk.CTk()
root.title("Bunker Code Helper — Setup")
root.geometry("620x760")
root.minsize(560, 700)

wrap = ctk.CTkScrollableFrame(root, fg_color="transparent")
wrap.pack(fill="both", expand=True, padx=18, pady=18)

ctk.CTkLabel(wrap, text="Bunker Code Helper",
             font=("Segoe UI", 26, "bold")).pack(anchor="w")
ctk.CTkLabel(wrap, text="Press a hotkey → screenshot → AI answers with numbers.",
             text_color="#9aa0b5").pack(anchor="w", pady=(0, 4))

warn = ctk.CTkLabel(
    wrap, wraplength=540, justify="left", text_color="#ffb020",
    text="⚠ Use at your own risk. Automating a game can get an account banned. "
         "Your API key is stored locally in app/config and never committed to git.")
warn.pack(anchor="w", pady=(4, 14))


def card(title):
    c = ctk.CTkFrame(wrap, corner_radius=14)
    c.pack(fill="x", pady=8)
    ctk.CTkLabel(c, text=title, font=("Segoe UI", 15, "bold")).pack(
        anchor="w", padx=16, pady=(12, 4))
    return c


# --- provider + key ---------------------------------------------------------
c1 = card("AI provider")
provider = ctk.StringVar(value=s.get("provider", "gemini"))
row = ctk.CTkFrame(c1, fg_color="transparent")
row.pack(fill="x", padx=16, pady=4)
ctk.CTkSegmentedButton(row, values=["gemini", "openai"], variable=provider,
                       selected_color=ACCENT).pack(side="left")

ctk.CTkLabel(c1, text="API key", text_color="#9aa0b5").pack(anchor="w", padx=16,
                                                            pady=(10, 0))
key_row = ctk.CTkFrame(c1, fg_color="transparent")
key_row.pack(fill="x", padx=16, pady=(2, 6))
key_entry = ctk.CTkEntry(key_row, show="•", placeholder_text="paste your API key")
key_entry.pack(side="left", fill="x", expand=True)
key_entry.insert(0, s.get("api_key", ""))


def toggle_key():
    key_entry.configure(show="" if key_entry.cget("show") else "•")


ctk.CTkButton(key_row, text="👁", width=40, command=toggle_key).pack(side="left",
                                                                    padx=(8, 0))

ctk.CTkLabel(c1, text="Model (leave blank for default)",
             text_color="#9aa0b5").pack(anchor="w", padx=16, pady=(8, 0))
model_entry = ctk.CTkEntry(c1)
model_entry.pack(fill="x", padx=16, pady=(2, 4))
model_entry.insert(0, s.get("model", ""))
model_hint = ctk.CTkLabel(c1, text="", text_color="#6a7088", font=("Segoe UI", 11))
model_hint.pack(anchor="w", padx=16, pady=(0, 6))

# base_url: only used when provider = openai (any OpenAI-compatible endpoint)
base_lbl = ctk.CTkLabel(c1, text="API base URL (OpenAI-compatible only)",
                        text_color="#9aa0b5")
base_lbl.pack(anchor="w", padx=16, pady=(4, 0))
base_entry = ctk.CTkEntry(c1, placeholder_text="blank = api.openai.com")
base_entry.pack(fill="x", padx=16, pady=(2, 8))
base_entry.insert(0, s.get("base_url", ""))


# --- per-provider key memory ------------------------------------------------
def key_id(prov, burl):
    if prov == "gemini":
        return "gemini"
    b = burl or "https://api.openai.com/v1"
    for k in ("nvidia", "groq", "mistral", "openrouter", "localhost", "127.0.0.1"):
        if k in b:
            return k
    return "openai"


saved_keys = dict(s.get("keys", {}))
_kid0 = key_id(s.get("provider", "gemini"), s.get("base_url", ""))
if s.get("api_key") and _kid0 not in saved_keys:      # migrate the old single key
    saved_keys[_kid0] = s["api_key"]


def _remember_current_key():
    k = key_entry.get().strip()
    if k and k != "ollama":
        saved_keys[key_id(provider.get(), base_entry.get().strip())] = k


def upd_hint(*_):
    model_hint.configure(text=f"default: {MODEL_HINT[provider.get()]}")
    show_base = provider.get() == "openai"
    if show_base:
        base_lbl.pack(anchor="w", padx=16, pady=(4, 0))
        base_entry.pack(fill="x", padx=16, pady=(2, 8))
    else:
        base_lbl.pack_forget()
        base_entry.pack_forget()


provider.trace_add("write", upd_hint)

# --- one-click presets ------------------------------------------------------
ctk.CTkLabel(c1, text="Quick preset", text_color="#9aa0b5").pack(
    anchor="w", padx=16, pady=(2, 0))
preset_row = ctk.CTkFrame(c1, fg_color="transparent")
preset_row.pack(fill="x", padx=12, pady=(2, 12))


def apply_preset(name):
    _remember_current_key()                          # keep the key we're leaving
    prov, burl, mdl = PRESETS[name]
    provider.set(prov)
    base_entry.delete(0, "end"); base_entry.insert(0, burl)
    model_entry.delete(0, "end"); model_entry.insert(0, mdl)
    nid = key_id(prov, burl)
    key_entry.delete(0, "end")
    if nid in saved_keys:                             # restore this provider's key
        key_entry.insert(0, saved_keys[nid])
    elif "localhost" in burl or "127.0.0.1" in burl:  # local Ollama: no real key
        key_entry.insert(0, "ollama")


for _name in PRESETS:
    ctk.CTkButton(preset_row, text=_name, height=28, fg_color="#3a3f55",
                  font=("Segoe UI", 11),
                  command=lambda n=_name: apply_preset(n)).pack(
        side="left", padx=4, pady=2)

upd_hint()

# --- solving ----------------------------------------------------------------
c_solve = card("Solving")
local_math = ctk.BooleanVar(value=s.get("local_math", True))
ctk.CTkCheckBox(c_solve, text="Compute math locally in Python (recommended)",
                variable=local_math).pack(anchor="w", padx=16, pady=(2, 2))
ctk.CTkLabel(c_solve, wraplength=520, justify="left", text_color="#6a7088",
             font=("Segoe UI", 11),
             text="The AI only READS the tasks; arithmetic is recomputed in Python "
                  "(100% accurate — fixes models that misread the math). Word problems "
                  "and riddles still use the AI's answer. Turn off to use your custom "
                  "prompt and the AI's raw answer.").pack(anchor="w", padx=16,
                                                          pady=(0, 12))

# --- hotkeys ----------------------------------------------------------------
c2 = card("Hotkeys")
hk_row = ctk.CTkFrame(c2, fg_color="transparent")
hk_row.pack(fill="x", padx=16, pady=(2, 12))
ctk.CTkLabel(hk_row, text="Screenshot + solve").pack(side="left")
hotkey_entry = ctk.CTkEntry(hk_row, width=110, justify="center")
hotkey_entry.pack(side="left", padx=10)
hotkey_entry.insert(0, s.get("hotkey", "end"))
ctk.CTkLabel(hk_row, text="Quit").pack(side="left", padx=(20, 0))
quit_entry = ctk.CTkEntry(hk_row, width=90, justify="center")
quit_entry.pack(side="left", padx=10)
quit_entry.insert(0, s.get("quit_hotkey", "f8"))

# --- prompt -----------------------------------------------------------------
c3 = card("Extra instructions (added to the built-in prompt)")
ctk.CTkLabel(c3, wraplength=520, justify="left", text_color="#6a7088",
             font=("Segoe UI", 11),
             text="Optional. Appended to the built-in prompt in BOTH modes — use it "
                  "for tweaks like 'ignore the killfeed on the right'. Leave empty to "
                  "use the built-in prompt as-is.").pack(anchor="w", padx=16, pady=(0, 4))
prompt_box = ctk.CTkTextbox(c3, height=80, wrap="word")
prompt_box.pack(fill="x", padx=16, pady=(2, 6))
prompt_box.insert("1.0", s.get("prompt", DEFAULT_PROMPT))
ctk.CTkButton(c3, text="Clear", width=140, fg_color="#3a3f55",
              command=lambda: prompt_box.delete("1.0", "end")
              ).pack(anchor="e", padx=16, pady=(0, 12))

# --- advanced ---------------------------------------------------------------
c4 = card("Overlay & image")
adv = ctk.CTkFrame(c4, fg_color="transparent")
adv.pack(fill="x", padx=16, pady=(2, 12))
ctk.CTkLabel(adv, text="Answer shown for (sec)").grid(row=0, column=0, sticky="w",
                                                      pady=4)
sec_entry = ctk.CTkEntry(adv, width=70, justify="center")
sec_entry.grid(row=0, column=1, padx=10)
sec_entry.insert(0, str(s.get("overlay_seconds", 6)))
ctk.CTkLabel(adv, text="Max upload width (px, 0=off)").grid(row=1, column=0,
                                                            sticky="w", pady=4)
mw_entry = ctk.CTkEntry(adv, width=70, justify="center")
mw_entry.grid(row=1, column=1, padx=10)
mw_entry.insert(0, str(s.get("max_width", 1280)))
ctk.CTkLabel(adv, text="Capture area").grid(row=2, column=0, sticky="w", pady=4)
region = ctk.StringVar(value=s.get("region", "full"))
ctk.CTkOptionMenu(adv, width=110, variable=region,
                  values=["full", "right", "left"]).grid(row=2, column=1, padx=10)
ctk.CTkLabel(adv, text="'right' = only the right half (tasks side); smaller & clearer",
             text_color="#6a7088", font=("Segoe UI", 11)).grid(
    row=3, column=0, columnspan=2, sticky="w", pady=(0, 4))

# --- save -------------------------------------------------------------------
status = ctk.CTkLabel(wrap, text="", text_color=OK)
status.pack(anchor="w", pady=(6, 0))


def _int(entry, default):
    try:
        return int(float(entry.get()))
    except Exception:
        return default


def save():
    _remember_current_key()
    data = {
        "provider": provider.get(),
        "api_key": key_entry.get().strip(),
        "base_url": base_entry.get().strip(),
        "model": model_entry.get().strip(),
        "keys": saved_keys,
        "hotkey": hotkey_entry.get().strip().lower() or "end",
        "quit_hotkey": quit_entry.get().strip().lower() or "f8",
        "prompt": prompt_box.get("1.0", "end").strip() or DEFAULT_PROMPT,
        "region": region.get(),
        "local_math": bool(local_math.get()),
        "overlay_seconds": _int(sec_entry, 6),
        "max_width": _int(mw_entry, 1280),
        "jpeg_quality": s.get("jpeg_quality", 70),
    }
    with open(os.path.join(CFG, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # create run.bat in the project root
    bat = ("@echo off\r\n"
           'cd /d "%~dp0app"\r\n'
           "title Bunker Code Helper\r\n"
           "python bunker_code_helper.py\r\n"
           "pause\r\n")
    with open(os.path.join(ROOT, "run.bat"), "w", encoding="utf-8") as f:
        f.write(bat)

    msg = "✔ Saved. Launch the helper with run.bat"
    if not data["api_key"]:
        msg = "✔ Saved, but no API key — paste one before running."
    status.configure(text=msg)


ctk.CTkButton(wrap, text="Save & create run.bat", height=44, fg_color=ACCENT,
              font=("Segoe UI", 15, "bold"), command=save).pack(fill="x", pady=(6, 4))

root.mainloop()
