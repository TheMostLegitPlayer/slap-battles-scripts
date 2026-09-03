"""
Bunker Code Helper. Press the hotkey (End) -> screenshot -> Gemini/OpenAI ->
answer shown in an overlay box. Set it up with setup.bat / linux/setup.sh.
"""
import os
import io
import re
import ast
import sys
import json
import time
import queue
import base64
import platform
import threading
import tkinter as tk

APP = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(APP, "config")
IS_WIN = platform.system() == "Windows"

# keyboard lib on Windows, pynput elsewhere (pynput needs no root on X11)
try:
    import requests
    from PIL import Image
    import mss
    if IS_WIN:
        import keyboard as _kbd
    else:
        from pynput import keyboard as _pynput
except ImportError as e:
    print(f"[!] Missing dependency: {e.name}")
    print("    Run setup first (it installs everything): setup.bat (Windows) or "
          "linux/setup.sh (Linux).")
    try:
        input("Press Enter to close...")
    except EOFError:
        pass
    sys.exit(1)

DEFAULTS = {
    "provider": "gemini",              # gemini | openai (openai-compatible)
    "api_key": "",
    "base_url": "",                    # openai provider: blank = OpenAI, else NIM/Groq/Ollama
    "model": "",
    "hotkey": "end",
    "quit_hotkey": "f8",
    "region": "full",                  # full | right | left
    "local_math": True,                # AI reads, Python does the arithmetic
    "prompt": "",
    "overlay_seconds": 6,
    "jpeg_quality": 70,
    "max_width": 1280,
}
MODEL_DEFAULTS = {"gemini": "gemini-3.5-flash-lite", "openai": "gpt-4o-mini"}

PLAIN_PROMPT = (
    "This is a Slap Battles 'bunker code' board with several task panels; each panel's "
    "answer is a SINGLE digit (0-9). IGNORE the game HUD/stats at the top and edges "
    "(ping, FPS, CPU, players, chat). Solve each panel top to bottom and reply with "
    "ONLY the digits separated by spaces (one digit per task), nothing else - e.g. "
    "'4 3 6 2'. Never output a multi-digit number for a single task."
)

# local-math mode: model just reads each task, Python recomputes the arithmetic
STRUCT_PROMPT = (
    "This is a Slap Battles 'bunker code' board: several task panels, and each "
    "panel's answer is a SINGLE digit (0-9). IGNORE the game HUD and any stats at the "
    "top or edges of the screen (ping, FPS, CPU, player list, chat, timers). "
    "For EACH task panel, top to bottom, output ONE line: the task copied verbatim "
    "(join any wrapped text into a single line, keep math symbols like ^ x ÷ and "
    "parentheses), then ' ||| ', then its single-digit answer. Output nothing else."
)

# known task pool -> answer, matched fuzzily against what's on screen
TASKS = [
    ("4", "185,634-185,629+185,632-185,633"),
    ("2", "80+0-8+15-(85)"),
    ("3", "18x18-18+18-321"),
    ("9", "There are 120 seconds on the timer, Karl spends 30 seconds eating a "
          "hotdog, 68 seconds crying and 13 seconds punching people. How many "
          "seconds are left?"),
    ("8", "Bob has been alive for centuries living off the people he has absorbed. "
          "You may think you are safe but you're not. You never are. What number is "
          "infinity sideways"),
    ("2", "Bob had 20 pink balloons. He gave 12 to his friends. Some mean people came "
          "and popped 6 of his balloons. He replaced them with 8 red balloons. How "
          "many pink balloons does Bob have?"),
    ("8", "(690-685)+(42-39)"),
    ("3", "78x3-140+32-123"),
    ("7", "√64 - 3 + 2"),
    ("8", "(61x2) - (38x3)"),
    ("2", "9^2(6x48) - 23,326"),
    ("6", "There are 500 apples in total. Bob gets 382, Rob gets 112. How many "
          "apples are left?"),
    ("3", "17^2 - 286"),
    ("6", "(36x2) ÷ 12"),
    ("6", "9(52 ÷ 3) - 150"),
    ("2", "16x63-1006"),
]


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


_TASK_NORM = [(_norm(txt), ans) for ans, txt in TASKS]


def match_task(line, threshold=0.55):
    """Return the known answer for the closest task in the pool, or None."""
    import difflib
    n = _norm(line)
    if len(n) < 3:
        return None
    best_ans, best_ratio = None, 0.0
    for tn, ans in _TASK_NORM:
        r = difflib.SequenceMatcher(None, n, tn).ratio()
        if r > best_ratio:
            best_ratio, best_ans = r, ans
    return best_ans if best_ratio >= threshold else None


_ALLOWED_AST = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd,
                ast.Mod, ast.FloorDiv)


def evaluate(expr):
    """Safely evaluate an arithmetic expression written in game notation."""
    s = expr.strip().replace(",", "")
    s = s.replace("×", "*").replace("x", "*").replace("X", "*")
    s = s.replace("÷", "/").replace("−", "-").replace("–", "-")
    s = s.replace("^", "**").replace(" ", "")
    s = re.sub(r"(\d|\))(\()", r"\1*\2", s)     # 9(..) -> 9*(..), 2( -> 2*(
    s = re.sub(r"(\))(\d)", r"\1*\2", s)        # )(  and )9
    node = ast.parse(s, mode="eval")
    for n in ast.walk(node):
        if not isinstance(n, _ALLOWED_AST):
            raise ValueError("unsafe token: " + type(n).__name__)
    v = eval(compile(node, "<expr>", "eval"))
    return round(v) if abs(v - round(v)) < 1e-6 else v


def _is_arith(s):
    return bool(re.search(r"\d", s)) and re.fullmatch(
        r"[\d\s\+\-\*/×÷xX\^\(\)\.,=]+", s.strip()) is not None


def format_code(ans):
    """When every task resolved to a single digit, also show the joined code so it's
    unambiguous, e.g. '4 3 6 2   ->   4362'."""
    parts = ans.split()
    if len(parts) > 1 and all(len(p) == 1 and p.isdigit() for p in parts):
        return f"{' '.join(parts)}   →   {''.join(parts)}"
    return ans


def parse_structured(raw):
    """Turn the model's 'task ||| answer' lines into a numbers-only string,
    recomputing every arithmetic task in Python."""
    out = []
    for line in raw.splitlines():
        if "|||" not in line:
            continue
        left, right = line.split("|||", 1)
        hit = match_task(left)                          # known task -> known answer
        if hit is not None:
            out.append(hit)
            continue
        if _is_arith(left):                             # else compute it here
            try:
                out.append(str(evaluate(left)))
                continue
            except Exception:
                pass
        m = re.search(r"-?\d+(?:\.\d+)?", right)         # else trust the model

        out.append(m.group() if m else "?")
    return " ".join(out) if out else raw.strip()


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(os.path.join(CFG, "settings.json"), encoding="utf-8") as f:
            s.update(json.load(f))
    except Exception:
        pass
    if not s.get("model"):
        s["model"] = MODEL_DEFAULTS.get(s["provider"], "")
    return s


# borderless top-most box, updated through a queue so it never steals focus
BG = "#1a1a2e"
SENT_COLOR = "#00ff88"
ANSWER_COLOR = "#ffcc00"
ERROR_COLOR = "#ff6b6b"


class Overlay:
    def __init__(self):
        self._q = queue.Queue()
        self._hide_at = 0
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)
        try:
            self.root.attributes("-disabled", True)   # Windows: never grab focus
        except Exception:
            pass
        self.root.configure(bg=BG)
        self.label = tk.Label(self.root, text="", font=("Segoe UI", 22, "bold"),
                              fg=SENT_COLOR, bg=BG, padx=28, pady=20,
                              justify="center", wraplength=900)
        self.label.pack(expand=True, fill="both")
        self.root.withdraw()
        self._poll()
        self.root.mainloop()

    def _place(self):
        self.root.update_idletasks()
        w = self.label.winfo_reqwidth()
        h = self.label.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        x = (sw - w) // 2
        self.root.geometry(f"{w}x{h}+{x}+60")

    def _poll(self):
        try:
            while True:
                text, color, seconds, size = self._q.get_nowait()
                self.label.configure(text=text, fg=color,
                                     font=("Segoe UI", size, "bold"))
                self._place()
                self.root.deiconify()
                self.root.lift()
                self._hide_at = (time.time() + seconds) if seconds else 0
        except queue.Empty:
            pass
        if self._hide_at and time.time() >= self._hide_at:
            self.root.withdraw()
            self._hide_at = 0
        self.root.after(40, self._poll)

    def show(self, text, color=SENT_COLOR, seconds=0, size=22):
        """seconds=0 keeps the box up until the next show() replaces it."""
        self._q.put((text, color, seconds, size))


overlay = Overlay()


_MSS = getattr(mss, "MSS", None) or mss.mss     # new/old mss API

# some providers (NIM) cap inline base64 around 180 KB, keep under it
MAX_B64 = 175_000


def _encode(img, quality):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def grab_jpeg(max_width, quality, max_b64=MAX_B64, region="full"):
    with _MSS() as sct:
        mon = sct.monitors[1]                      # primary monitor
        raw = sct.grab(mon)
        img = Image.frombytes("RGB", raw.size, raw.rgb)
    if region == "right":                           # tasks sit on the right side
        img = img.crop((img.width // 2, 0, img.width, img.height))
    elif region == "left":
        img = img.crop((0, 0, img.width // 2, img.height))
    if max_width and img.width > max_width:
        h = int(img.height * max_width / img.width)
        img = img.resize((max_width, h), Image.LANCZOS)
    jpeg = _encode(img, quality)
    # shrink until it fits the size cap
    while max_b64 and (len(jpeg) * 4) // 3 > max_b64 and img.width > 480:
        img = img.resize((int(img.width * 0.85), int(img.height * 0.85)),
                         Image.LANCZOS)
        jpeg = _encode(img, quality)
    return jpeg


# ---------------------------------------------------------------- LLM calls
def _post_retry(url, *, json_body, headers=None, timeout=60, retries=3, label=""):
    """POST with a short backoff on timeouts and 429/5xx."""
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(url, json=json_body, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last = RuntimeError(f"{label} network error: {e}")
        else:
            if r.status_code == 200:
                return r
            if r.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"{label} {r.status_code}: {r.text[:200]}")
            last = RuntimeError(f"{label} {r.status_code}: {r.text[:120]}")
        if attempt < retries - 1:
            print(f"[retry {attempt+1}/{retries-1}] {last}", flush=True)
            time.sleep(1.5 * (attempt + 1))
    raise last or RuntimeError(f"{label} request failed")


def ask_gemini(key, model, prompt, jpeg):
    b64 = base64.b64encode(jpeg).decode()
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
        ]}],
        "generationConfig": {"temperature": 0},
    }
    r = _post_retry(url, json_body=body, label="Gemini")
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def ask_openai(key, model, prompt, jpeg, base_url=""):
    """OpenAI or any OpenAI-compatible endpoint (point base_url at their /v1)."""
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    b64 = base64.b64encode(jpeg).decode()
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
    }
    r = _post_retry(f"{base}/chat/completions", json_body=body,
                    headers={"Authorization": f"Bearer {key}"})
    return r.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------- hotkeys
def _to_pynput(hk):
    """'end' -> '<end>', 'f8' -> '<f8>', 'ctrl+alt+q' -> '<ctrl>+<alt>+q'."""
    return "+".join(p if len(p) == 1 else f"<{p}>" for p in hk.split("+"))


def run_hotkeys(mapping):
    """mapping: {hotkey_string: callable}. Blocks forever, listening."""
    if IS_WIN:
        for hk, fn in mapping.items():
            _kbd.add_hotkey(hk, fn)
        _kbd.wait()
    else:
        conv = {_to_pynput(hk): fn for hk, fn in mapping.items()}
        with _pynput.GlobalHotKeys(conv) as h:
            h.join()


# ---------------------------------------------------------------- main flow
BUSY = threading.Lock()


def on_trigger(s):
    if not BUSY.acquire(blocking=False):
        return                                     # already working on one
    threading.Thread(target=_work, args=(s,), daemon=True).start()


def _who(s):
    if s["provider"] == "gemini":
        return "Gemini"
    b = s.get("base_url", "")
    for k, name in (("nvidia", "NVIDIA"), ("groq", "Groq"),
                    ("mistral", "Mistral"), ("openrouter", "OpenRouter"),
                    ("localhost", "Ollama"), ("127.0.0.1", "Ollama")):
        if k in b:
            return name
    return "OpenAI"


def _work(s):
    try:
        who = _who(s)
        local_math = s.get("local_math", True)
        base = STRUCT_PROMPT if local_math else PLAIN_PROMPT
        extra = (s.get("prompt") or "").strip()        # user's extra notes from setup
        prompt = base + ("\n\n" + extra if extra else "")
        overlay.show(f"\U0001F4F8  Sent to {who}…", SENT_COLOR, 0, 22)
        t0 = time.time()
        jpeg = grab_jpeg(s["max_width"], s["jpeg_quality"],
                         region=s.get("region", "full"))
        if s["provider"] == "gemini":
            ans = ask_gemini(s["api_key"], s["model"], prompt, jpeg)
        else:
            ans = ask_openai(s["api_key"], s["model"], prompt, jpeg,
                             s.get("base_url", ""))
        dt = time.time() - t0
        if local_math:
            print(f"[{who} raw] {ans.strip()}")
            ans = parse_structured(ans)
        ans = ans.strip() or "(empty answer)"
        ans = format_code(ans)
        print(f"[{who} {dt:.1f}s] {ans}")
        # big answer, highlighted the same way the sent box was
        size = 40 if len(ans) <= 24 else 26
        overlay.show(ans, ANSWER_COLOR, s["overlay_seconds"], size)
    except Exception as e:
        print(f"[!] {e}")
        overlay.show(f"Error: {e}", ERROR_COLOR, 5, 16)
    finally:
        BUSY.release()


def main():
    s = load_settings()
    print("=" * 56)
    print(" Bunker Code Helper")
    print("=" * 56)
    is_local = any(h in s.get("base_url", "") for h in ("localhost", "127.0.0.1"))
    if not s["api_key"] and not is_local:
        print("[!] No API key set. Run setup and paste your key first.")
        try:
            input("Press Enter to close...")
        except EOFError:
            pass
        return
    print(f" Provider : {_who(s)}  (model: {s['model']})")
    print(f" Math     : {'local Python (accurate)' if s.get('local_math', True) else 'AI raw answer'}")
    print(f" Hotkey   : {s['hotkey'].upper()}  ->  screenshot + solve")
    print(f" Quit     : {s['quit_hotkey'].upper()}")
    print("=" * 56)
    if not IS_WIN:
        print(" (Linux: global hotkeys use pynput — works on X11 as a normal user.)")
    overlay.show(f"Ready — press {s['hotkey'].upper()}", SENT_COLOR, 3, 20)

    def _quit():
        print("Bye.")
        os._exit(0)

    run_hotkeys({s["hotkey"]: lambda: on_trigger(s), s["quit_hotkey"]: _quit})


if __name__ == "__main__":
    main()
