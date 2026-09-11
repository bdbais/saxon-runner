"""
SaxonRunner.pyw  v3.0 — Saxon XSLT GUI Runner + Local AI Assistant
New in v3:
  • AIClient       — Ollama / LM Studio / any OpenAI-compatible local endpoint
  • Autocomplete   — debounced popup while typing XSLT
  • AI Error Check — sends XSLT to LLM, marks issues in editor + explains them
  • AI Chat Panel  — streaming assistant embedded in the editor tab
  • AI Settings    — endpoint, model, autocomplete toggle, connection test
Requires only the Python standard library.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import subprocess, threading, json, os, re, time
import urllib.request, urllib.error
from datetime import datetime

# ── Color palette ────────────────────────────────────────────────────────────
C = dict(
    bg="#1e1e2e", bg2="#252535", bg3="#2a2a3d",
    panel="#16161e", border="#3a3a52",
    text="#cdd6f4", text_dim="#6c7086",
    accent="#89b4fa", accent2="#cba6f7",
    success="#a6e3a1", warning="#f9e2af",
    error="#f38ba8",  error_bg="#2d1a1a",
    info="#89dceb",
    search_hl="#45475a", search_cur="#f9e2af",
    btn_bg="#313244", btn_hover="#45475a",
    run_bg="#a6e3a1", run_fg="#1e1e2e",
    stop_bg="#f38ba8", stop_fg="#1e1e2e",
    watch_on="#cba6f7", watch_off="#45475a",
    ai_on="#f9e2af",   ai_dim="#45475a",
    ai_bg="#0e0e1c",   ai_user="#cba6f7",
    ai_ass="#89b4fa",  ai_sys="#6c7086",
    ai_thinking="#f9e2af",
    comp_bg="#1a1a30", comp_sel="#264f78",
    # Editor
    ed_bg="#0d0d1a", ed_gutter="#141422", ed_gutter_fg="#454560",
    ed_cursor="#cdd6f4", ed_curline="#1a1a2e", ed_sel="#264f78",
    ed_err_bg="#2d1111", ed_warn_bg="#2a2200",
    # Syntax
    hl_comment="#6a9955", hl_string="#ce9178", hl_xpath="#c586c0",
    hl_xsl="#569cd6",     hl_xml="#9cdcfe",    hl_attr="#9cdcfe",
    hl_punct="#666680",   hl_entity="#4ec9b0",  hl_number="#b5cea8",
)

FONT_MONO   = ("Consolas", 9)
FONT_MONO_B = ("Consolas", 9,  "bold")
FONT_MONO_S = ("Consolas", 8)
FONT_UI     = ("Segoe UI",  9)
FONT_UI_B   = ("Segoe UI",  9,  "bold")
FONT_SMALL  = ("Segoe UI",  8)

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".saxon_runner_config.json")

AI_SYSTEM_XSLT = (
    "Sei un esperto di XSLT 2.0/3.0, XPath e Saxon. "
    "Rispondi in italiano in modo conciso e pratico. "
    "Quando mostri codice XSLT usa blocchi ```xslt. "
    "Quando l'utente ti manda lo stylesheet corrente, "
    "usalo come contesto per rispondere alle domande."
)

AI_SYSTEM_COMPLETE = (
    "Sei un motore di completamento codice XSLT. "
    "Dato il codice con [CURSOR] che indica la posizione del cursore, "
    "fornisci esattamente 3 brevi completamenti alternativi. "
    "Formato: una riga per completamento, inizia con '1. ' '2. ' '3. '. "
    "Ogni completamento al massimo 15 token. Nessuna spiegazione."
)

AI_SYSTEM_CHECK = (
    "Sei un analizzatore di codice XSLT. "
    "Analizza il foglio di stile fornito e riporta problemi. "
    "Formato per ogni problema: LINE <n>: [ERROR|WARNING|INFO] <descrizione breve>\n"
    "Se non ci sono problemi rispondi solo con: OK\n"
    "Riporta solo errori reali, non preferenze stilistiche."
)

SUGGESTIONS = {
    "XPST0003":("Sintassi XPath non valida",
                "Controlla parentesi, virgolette e operatori. In XPath usa 'and'/'or'."),
    "XPST0081":("Prefisso namespace non dichiarato",
                "Aggiungi  xmlns:prefix='uri'  all'elemento radice del foglio."),
    "XPST0051":("Tipo non riconosciuto",
                "Verifica il nome nella dichiarazione  xs:  o  as=."),
    "XTSE0010":("Elemento non permesso in questo contesto",
                "Controlla la struttura XSLT: questo figlio non è valido qui."),
    "XTSE0020":("Attributo obbligatorio mancante",
                "Verifica gli attributi richiesti per questo elemento XSLT."),
    "XTSE0080":("Template con nome duplicato",
                "Esiste già un  xsl:template  con questo nome nel foglio."),
    "XTSE0340":("Variabile o parametro duplicato",
                "Questo nome è già usato nello stesso scope."),
    "XTSE0630":("Attributo non valido",
                "Questo attributo non è consentito su questo elemento XSLT."),
    "XPDY0002":("Nodo contesto non disponibile",
                "Stai usando '.' o un asse senza contesto disponibile."),
    "XPTY0004":("Errore di tipo",
                "Il tipo dell'espressione non corrisponde al tipo atteso."),
    "XPTY0019":("Non è un nodo",
                "L'espressione deve produrre un nodo, non un valore atomico."),
    "XTDE0030":("Template non trovato",
                "Nessun  xsl:template  corrisponde a questo pattern."),
    "XTDE0260":("Parametro obbligatorio non fornito",
                "Il parametro richiesto non è stato passato alla chiamata."),
    "SXXP0003":("XML sorgente non valido",
                "Il file XML di input non è ben formato. Controlla la sintassi XML."),
    "FODC0002":("Documento non trovato",
                "Il file specificato non esiste o non è accessibile."),
}

_XSLT_HL = [
    ("hl_comment", re.compile(r'<!--[\s\S]*?-->')),
    ("hl_string",  re.compile(r'"[^"<\n]*"|\'[^\'<\n]*\'')),
    ("hl_xpath",   re.compile(r'\{[^}\n]*\}')),
    ("hl_xsl",     re.compile(r'</?xsl:[a-zA-Z][\w-]*')),
    ("hl_xml",     re.compile(r'</?[a-zA-Z][a-zA-Z0-9_:.\-]*')),
    ("hl_punct",   re.compile(r'/>|</?|>')),
    ("hl_attr",    re.compile(r'\b([a-zA-Z][a-zA-Z0-9_:.\-]*)(?=\s*=)')),
    ("hl_entity",  re.compile(r'&(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]\w*);')),
    ("hl_number",  re.compile(r'\b\d+(?:\.\d+)?\b')),
]

_LOC_RE  = re.compile(
    r'on line (\d+)(?:\s+column\s+(\d+))?\s+of\s+(file:///\S+|\S[\S]*?\.xsl[t]?)', re.I)
_CODE_RE = re.compile(r'\b(X[A-Z]{3}\d{4}|SXXP\d{4})\b')

_NO_AC_KEYS = {
    'Escape','Return','KP_Enter','Tab','BackSpace','Delete',
    'Home','End','Left','Right','Up','Down','Prior','Next',
    'Control_L','Control_R','Alt_L','Alt_R','Shift_L','Shift_R','Caps_Lock',
    'F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12',
}


# ============================================================================
# AIClient
# ============================================================================
class AIClient:
    """Communicates with any OpenAI-compatible local endpoint (Ollama, LM Studio…)."""

    STATUS_UNKNOWN  = "?"
    STATUS_OK       = "ok"
    STATUS_OFFLINE  = "offline"

    def __init__(self, config: dict):
        self.config = config
        self.status = self.STATUS_UNKNOWN

    # ── properties ────────────────────────────────────────────────────────────
    @property
    def endpoint(self) -> str:
        return self.config.get("ai_endpoint", "http://localhost:11434").rstrip("/")

    @property
    def model(self) -> str:
        return self.config.get("ai_model", "mistral")

    @property
    def enabled(self) -> bool:
        return self.config.get("ai_enabled", True)

    @property
    def ac_enabled(self) -> bool:
        return self.enabled and self.config.get("ai_autocomplete", True)

    @property
    def ac_delay(self) -> int:
        return max(300, int(self.config.get("ai_ac_delay", 700)))

    # ── HTTP helpers ──────────────────────────────────────────────────────────
    def _post(self, path: str, payload: dict, timeout=30):
        import socket as _socket
        url  = f"{self.endpoint}{path}"
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST")
        if timeout is None:
            # For streaming: short connect timeout, then unlimited read
            old = _socket.getdefaulttimeout()
            _socket.setdefaulttimeout(15)
            try:
                r = urllib.request.urlopen(req, timeout=15)
            finally:
                _socket.setdefaulttimeout(old)
            r.fp.raw._sock.settimeout(None)
            return r
        return urllib.request.urlopen(req, timeout=timeout)

    # ── ping ──────────────────────────────────────────────────────────────────
    def ping(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.endpoint}/v1/models", timeout=3)
            self.status = self.STATUS_OK
            return True
        except Exception:
            # Ollama root endpoint
            try:
                urllib.request.urlopen(self.endpoint, timeout=3)
                self.status = self.STATUS_OK
                return True
            except Exception:
                self.status = self.STATUS_OFFLINE
                return False

    def ping_async(self, callback):
        def worker():
            ok = self.ping()
            callback(ok)
        threading.Thread(target=worker, daemon=True).start()

    # ── single completion (no stream) ─────────────────────────────────────────
    def once(self, system: str, user: str, max_tokens: int = 300) -> str:
        payload = {
            "model":      self.model,
            "messages":   [{"role":"system","content":system},
                           {"role":"user",  "content":user}],
            "stream":     False,
            "temperature":0.05,
            "max_tokens": max_tokens,
        }
        try:
            with self._post("/v1/chat/completions", payload, timeout=90) as r:
                d = json.loads(r.read())
                return (d.get("choices",[{}])[0]
                         .get("message",{}).get("content",""))
        except Exception as ex:
            return f"[Errore AI: {ex}]"

    # ── streaming chat ────────────────────────────────────────────────────────
    def stream(self, messages: list, on_token, on_done=None):
        payload = {
            "model":      self.model,
            "messages":   messages,
            "stream":     True,
            "temperature":0.2,
        }

        def worker():
            try:
                with self._post("/v1/chat/completions", payload, timeout=None) as r:
                    for raw_line in r:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            chunk = json.loads(line)
                            delta = (chunk.get("choices",[{}])[0]
                                         .get("delta",{}).get("content",""))
                            if delta:
                                on_token(delta)
                        except Exception:
                            pass
            except Exception as ex:
                on_token(f"\n[Errore connessione AI: {ex}]\n"
                         f"Verifica che Ollama sia avviato su {self.endpoint}")
            finally:
                if on_done:
                    on_done()

        threading.Thread(target=worker, daemon=True).start()

    # ── XSLT-specific helpers ─────────────────────────────────────────────────
    def autocomplete(self, context_before: str, on_result):
        """Ask for 3 short completions. Calls on_result(list[str])."""
        user = f"Codice XSLT (il cursore è alla fine):\n```xslt\n{context_before}[CURSOR]\n```"

        def worker():
            raw = self.once(AI_SYSTEM_COMPLETE, user, max_tokens=150)
            items = []
            for line in raw.splitlines():
                m = re.match(r'^\d+\.\s*(.+)', line.strip())
                if m:
                    items.append(m.group(1).strip())
            if not items and raw.strip():
                items = [raw.strip()[:80]]
            on_result(items)

        threading.Thread(target=worker, daemon=True).start()

    def check_xslt(self, content: str, on_token, on_done=None):
        """Analyze XSLT streaming. on_token(str) per chunk, on_done(full_str) at end."""
        trimmed = content[:3000] + ("\n[... troncato ...]" if len(content) > 3000 else "")
        messages = [
            {"role": "system", "content": AI_SYSTEM_CHECK},
            {"role": "user",   "content": f"Analizza questo XSLT:\n```xslt\n{trimmed}\n```"},
        ]
        buf = [""]
        def _tok(t):
            buf[0] += t
            on_token(t)
        def _done():
            if on_done:
                on_done(buf[0])
        self.stream(messages, _tok, _done)


# ============================================================================
# CompletionPopup
# ============================================================================
class CompletionPopup(tk.Toplevel):
    """Small popup window showing autocomplete suggestions."""

    def __init__(self, parent_widget, suggestions: list, on_accept, on_dismiss):
        super().__init__(parent_widget)
        self.overrideredirect(True)
        self.configure(bg=C["border"])
        self._on_accept  = on_accept
        self._on_dismiss = on_dismiss
        self._suggestions = suggestions
        self._build(suggestions)
        self.bind("<FocusOut>", lambda e: self._dismiss())

    def _build(self, suggestions):
        h = min(len(suggestions), 6)
        self.lb = tk.Listbox(
            self, font=FONT_MONO, bg=C["comp_bg"], fg=C["text"],
            selectbackground=C["comp_sel"], selectforeground=C["text"],
            activestyle="none", borderwidth=0, highlightthickness=0,
            width=62, height=h, relief="flat")
        self.lb.pack(padx=1, pady=1)

        # hint at bottom
        self._hint = tk.Label(
            self, text="Tab/Enter: accetta  ·  ↑↓: naviga  ·  Esc: chiudi",
            font=FONT_MONO_S, bg=C["comp_bg"], fg=C["ai_sys"], anchor="w")
        self._hint.pack(fill="x", padx=4, pady=(0,2))

        for s in suggestions:
            label = s.replace('\n', ' ↵ ')[:80]
            self.lb.insert("end", f"  {label}")
        if suggestions:
            self.lb.selection_set(0)

        self.lb.bind("<Return>",   lambda e: (self._accept(), "break")[1])
        self.lb.bind("<Tab>",      lambda e: (self._accept(), "break")[1])
        self.lb.bind("<Escape>",   lambda e: self._dismiss())
        self.lb.bind("<Up>",       lambda e: (self._nav(-1), "break")[1])
        self.lb.bind("<Down>",     lambda e: (self._nav(+1), "break")[1])
        self.lb.bind("<Double-Button-1>", lambda e: self._accept())

    def position(self, x: int, y: int):
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.lb.focus_set()

    def _nav(self, d: int):
        cur = self.lb.curselection()
        idx = ((cur[0] if cur else 0) + d) % self.lb.size()
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(idx)
        self.lb.see(idx)

    def _accept(self):
        sel = self.lb.curselection()
        if sel:
            self._on_accept(self._suggestions[sel[0]])
        try: self.destroy()
        except Exception: pass

    def _dismiss(self):
        self._on_dismiss()
        try: self.destroy()
        except Exception: pass


# ============================================================================
# AIPanel  — streaming chat embedded in the editor
# ============================================================================
class AIPanel(tk.Frame):
    """Collapsible AI chat panel shown below the XSLT editor."""

    def __init__(self, parent, ai: AIClient, get_context_fn, **kw):
        super().__init__(parent, bg=C["ai_bg"], **kw)
        self._ai          = ai
        self._get_ctx     = get_context_fn
        self._history: list[dict] = []
        self._streaming   = False
        self._build()

    def _build(self):
        # header
        hdr = tk.Frame(self, bg=C["bg3"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="🤖 Assistente AI XSLT", font=FONT_UI_B,
                 bg=C["bg3"], fg=C["ai_on"]).pack(side="left", padx=10, pady=4)
        self._model_lbl = tk.Label(hdr, text="", font=FONT_SMALL,
                                   bg=C["bg3"], fg=C["text_dim"])
        self._model_lbl.pack(side="left", padx=2)
        _Btn(hdr, "🗑 Cancella", self.clear).pack(side="right", padx=4, pady=3)
        _Btn(hdr, "📋 Includi XSL", self._inject_xsl).pack(side="right", padx=2, pady=3)

        # chat history
        tf = tk.Frame(self, bg=C["ai_bg"])
        tf.pack(fill="both", expand=True)
        ys = tk.Scrollbar(tf, bg=C["bg3"])
        self.chat_txt = tk.Text(
            tf, wrap="word", font=FONT_MONO_S,
            bg=C["ai_bg"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=0, padx=8, pady=6,
            state="disabled", yscrollcommand=ys.set)
        ys.config(command=self.chat_txt.yview)
        ys.pack(side="right", fill="y")
        self.chat_txt.pack(side="left", fill="both", expand=True)

        self.chat_txt.tag_configure("user",     foreground=C["ai_user"],  font=FONT_UI_B)
        self.chat_txt.tag_configure("assistant",foreground=C["ai_ass"])
        self.chat_txt.tag_configure("system",   foreground=C["ai_sys"],   font=FONT_SMALL)
        self.chat_txt.tag_configure("thinking", foreground=C["ai_thinking"])
        self.chat_txt.tag_configure("code_blk", background=C["bg3"],
                                    font=FONT_MONO_S)
        self.chat_txt.tag_configure("err_tag",  foreground=C["error"])

        # input row
        inp = tk.Frame(self, bg=C["bg3"])
        inp.pack(fill="x", pady=(0,0))
        self._iv = tk.StringVar()
        self._entry = tk.Entry(inp, textvariable=self._iv, font=FONT_MONO_S,
                               bg=C["bg"], fg=C["text"],
                               insertbackground=C["text"],
                               relief="flat", bd=4)
        self._entry.pack(side="left", fill="x", expand=True, padx=(8,4), pady=6)
        self._entry.bind("<Return>",   lambda e: self.send())
        self._entry.bind("<KP_Enter>", lambda e: self.send())
        self._entry.bind("<Shift-Return>", lambda e: self._newline())
        self._send_btn = _Btn(inp, "↵ Invia", self.send, accent=True)
        self._send_btn.pack(side="left", padx=(0,6), pady=4)

        self._update_model_label()

    # ── public ────────────────────────────────────────────────────────────────
    def focus_input(self):
        self._entry.focus_set()

    def clear(self):
        self._history = []
        self.chat_txt.config(state="normal")
        self.chat_txt.delete("1.0","end")
        self.chat_txt.config(state="disabled")

    def send(self, prefilled: str = ""):
        if self._streaming:
            return
        msg = (prefilled or self._iv.get()).strip()
        if not msg:
            return
        self._iv.set("")

        # build messages
        xslt_ctx = self._get_ctx()
        sys_msg = AI_SYSTEM_XSLT
        if xslt_ctx.strip():
            sys_msg += (f"\n\nStai lavorando su questo stylesheet:\n"
                        f"```xslt\n{xslt_ctx[:4000]}\n```")

        if not self._history:
            self._history.append({"role":"system","content":sys_msg})
        self._history.append({"role":"user","content":msg})

        self._append("Tu", msg + "\n\n", "user")
        self._append("AI", "", "thinking")
        self._streaming = True
        self._send_btn.config(state="disabled", text="…")
        dot_idx = self.chat_txt.index("end-1c")

        buf = [""]

        def on_token(tok):
            if tok.startswith("\n[Errore"):
                self.chat_txt.config(state="normal")
                self.chat_txt.insert("end", tok, "err_tag")
                self.chat_txt.config(state="disabled")
                return
            self.chat_txt.config(state="normal")
            # replace "thinking" placeholder on first real token
            if not buf[0]:
                try:
                    self.chat_txt.delete(dot_idx, "end")
                except Exception:
                    pass
                self.chat_txt.insert("end", "\nAI  ", "assistant")
            buf[0] += tok
            self.chat_txt.insert("end", tok, "assistant")
            self.chat_txt.see("end")
            self.chat_txt.config(state="disabled")

        def on_done():
            self._history.append({"role":"assistant","content":buf[0]})
            self._streaming = False
            self.chat_txt.config(state="normal")
            self.chat_txt.insert("end","\n\n")
            self.chat_txt.config(state="disabled")
            self.chat_txt.see("end")
            self._send_btn.config(state="normal", text="↵ Invia")

        self._ai.stream(self._history, on_token, on_done)

    def show_check_result(self, raw: str, line_issues: list):
        """Show AI error check result in the chat."""
        self._append("✨ Analisi AI", raw + "\n\n", "assistant")
        if line_issues:
            self._append("",
                         f"↑ {len(line_issues)} riga/e marcate nell'editor.\n\n",
                         "system")

    def _inject_xsl(self):
        ctx = self._get_ctx()
        if ctx.strip():
            self._iv.set("")
            self.send(f"Analizza questo stylesheet e dammi un riassunto delle funzionalità principali:\n"
                      f"```xslt\n{ctx[:3000]}\n```")

    # ── internal ──────────────────────────────────────────────────────────────
    def _append(self, who: str, text: str, tag: str):
        self.chat_txt.config(state="normal")
        if who:
            self.chat_txt.insert("end", f"{who}  ", tag)
        if text:
            self.chat_txt.insert("end", text, tag)
        self.chat_txt.see("end")
        self.chat_txt.config(state="disabled")

    def _newline(self):
        self._iv.set(self._iv.get() + "\n")

    def _update_model_label(self):
        self._model_lbl.config(
            text=f"[{self._ai.model}  ·  {self._ai.endpoint}]")


# ============================================================================
# FileWatcher
# ============================================================================
class FileWatcher:
    def __init__(self, callback, interval=0.8, debounce=0.4):
        self._cb       = callback
        self._interval = interval
        self._debounce = debounce
        self._files: dict = {}
        self._lock    = threading.Lock()
        self._running = False
        self._timer   = None

    @property
    def active(self): return self._running

    def set_files(self, *paths):
        with self._lock:
            self._files = {}
            for p in paths:
                if p and os.path.isfile(p):
                    try: self._files[p] = os.path.getmtime(p)
                    except OSError: pass

    def start(self):
        if self._running: return
        self._running = True
        threading.Thread(target=self._poll, daemon=True).start()

    def stop(self):
        self._running = False
        if self._timer: self._timer.cancel()

    def _poll(self):
        while self._running:
            changed = []
            with self._lock:
                for p, mt in list(self._files.items()):
                    try:
                        nmt = os.path.getmtime(p)
                        if nmt != mt:
                            self._files[p] = nmt
                            changed.append(p)
                    except OSError: pass
            if changed:
                if self._timer: self._timer.cancel()
                self._timer = threading.Timer(self._debounce, self._cb, (changed[0],))
                self._timer.daemon = True
                self._timer.start()
            time.sleep(self._interval)


# ============================================================================
# _Btn
# ============================================================================
class _Btn(tk.Button):
    def __init__(self, parent, text, command,
                 accent=False, run=False, stop=False, watch=False, **kw):
        if run:    bg, fg = C["run_bg"],  C["run_fg"]
        elif stop: bg, fg = C["stop_bg"], C["stop_fg"]
        elif watch:bg, fg = C["watch_on"],C["run_fg"]
        elif accent:bg,fg = C["accent"],  C["bg"]
        else:      bg, fg = C["btn_bg"],  C["text"]
        super().__init__(parent, text=text, command=command,
                         bg=bg, fg=fg, font=FONT_UI,
                         relief="flat", bd=0, padx=10, pady=4,
                         activebackground=C["btn_hover"],
                         activeforeground=fg, cursor="hand2", **kw)
        self._bg = bg
        self.bind("<Enter>", lambda _: self.config(
            bg=C["btn_hover"] if not (run or stop or accent or watch) else bg))
        self.bind("<Leave>", lambda _: self.config(bg=bg))


# ============================================================================
# XSLTEditor  (v3 — with AI)
# ============================================================================
class XSLTEditor(tk.Frame):

    def __init__(self, parent, ai: AIClient,
                 on_save=None, on_dirty_change=None, **kw):
        super().__init__(parent, bg=C["bg2"], **kw)
        self._ai         = ai
        self._filepath   = None
        self._dirty      = False
        self._on_save    = on_save
        self._on_dirty   = on_dirty_change
        self._hl_job     = None
        self._ac_job     = None
        self._popup      = None
        self._err_lines: list = []
        self._find_pos: list  = []
        self._find_cur: int   = -1
        self._find_open       = False
        self._ai_panel_open   = False
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────
    def _build(self):
        # ── toolbar ──
        tb = tk.Frame(self, bg=C["bg3"])
        tb.pack(fill="x")

        self._title_lbl = tk.Label(tb, text="Nessun file", font=FONT_UI_B,
                                   bg=C["bg3"], fg=C["text_dim"], anchor="w")
        self._title_lbl.pack(side="left", padx=10, pady=5)
        self._dirty_lbl = tk.Label(tb, text="", font=FONT_SMALL,
                                   bg=C["bg3"], fg=C["warning"])
        self._dirty_lbl.pack(side="left")

        for txt, cmd in [("💾 Salva", self.save_file),
                         ("📂 Apri…", self.open_dialog),
                         ("🔍 Trova", lambda: self._toggle_find(False)),
                         ("H Sostitui", lambda: self._toggle_find(True)),
                         ("↕ Riga", self._goto_dialog)]:
            _Btn(tb, txt, cmd).pack(side="left", padx=2, pady=4)

        # AI section
        sep = tk.Frame(tb, bg=C["border"], width=1)
        sep.pack(side="left", fill="y", padx=6, pady=4)

        self._ai_dot = tk.Label(tb, text="●", font=FONT_UI_B,
                                bg=C["bg3"], fg=C["ai_dim"])
        self._ai_dot.pack(side="left", padx=(0,2), pady=5)

        self._ac_btn = _Btn(tb, "✨ Check AI", self._ai_check_btn)
        self._ac_btn.pack(side="left", padx=2, pady=4)
        self._chat_btn = _Btn(tb, "🤖 Chat AI", self._toggle_ai_panel)
        self._chat_btn.pack(side="left", padx=2, pady=4)

        self._pos_lbl = tk.Label(tb, text="Ln 1  Col 1", font=FONT_SMALL,
                                 bg=C["bg3"], fg=C["text_dim"])
        self._pos_lbl.pack(side="right", padx=10)

        # ── find bar (hidden) ──
        self._fr = tk.Frame(self, bg=C["bg3"])
        self._build_findbar()

        # ── vertical pane: editor | ai panel ──
        self._vpane = ttk.PanedWindow(self, orient="vertical")
        self._vpane.pack(fill="both", expand=True)

        # editor area
        self._ed_frame = tk.Frame(self._vpane, bg=C["ed_bg"])
        self._vpane.add(self._ed_frame, weight=3)

        ea = self._ed_frame
        ys = tk.Scrollbar(ea, bg=C["bg2"])
        xs = tk.Scrollbar(ea, orient="horizontal", bg=C["bg2"])
        ys.pack(side="right",  fill="y")
        xs.pack(side="bottom", fill="x")

        self.gutter = tk.Text(ea, width=5, state="disabled", font=FONT_MONO,
                              bg=C["ed_gutter"], fg=C["ed_gutter_fg"],
                              relief="flat", bd=0, padx=6, pady=2,
                              cursor="arrow",
                              selectbackground=C["ed_gutter"])
        self.gutter.pack(side="left", fill="y")

        self.txt = tk.Text(ea, wrap="none", font=FONT_MONO,
                           bg=C["ed_bg"], fg=C["text"],
                           insertbackground=C["ed_cursor"],
                           selectbackground=C["ed_sel"],
                           relief="flat", bd=0, padx=8, pady=2,
                           undo=True, maxundo=200,
                           xscrollcommand=xs.set)
        self.txt.pack(side="left", fill="both", expand=True)
        xs.config(command=self.txt.xview)
        self.txt.configure(yscrollcommand=lambda *a:
                           (ys.set(*a), self._sync_gutter()))
        ys.config(command=self._yscroll)

        # syntax tags
        for tag, fg in [
            ("hl_comment",C["hl_comment"]),("hl_string",C["hl_string"]),
            ("hl_xpath",C["hl_xpath"]),    ("hl_xsl",C["hl_xsl"]),
            ("hl_xml",C["hl_xml"]),        ("hl_punct",C["hl_punct"]),
            ("hl_attr",C["hl_attr"]),      ("hl_entity",C["hl_entity"]),
            ("hl_number",C["hl_number"]),
        ]:
            kw = {"foreground": fg}
            if tag == "hl_xsl": kw["font"] = FONT_MONO_B
            self.txt.tag_configure(tag, **kw)

        self.txt.tag_configure("curline",   background=C["ed_curline"])
        self.txt.tag_configure("err_line",  background=C["ed_err_bg"])
        self.txt.tag_configure("warn_line", background=C["ed_warn_bg"])
        self.txt.tag_configure("hl_find",   background=C["search_hl"])
        self.txt.tag_configure("hl_find_cur",background=C["search_cur"],
                               foreground=C["bg"])
        self.gutter.tag_configure("err_g",  foreground=C["error"])
        self.gutter.tag_configure("warn_g", foreground=C["warning"])

        # AI panel (hidden initially)
        self._ai_panel = AIPanel(self._vpane, self._ai, self.get_content)

        # bindings
        self.txt.bind("<KeyRelease>",    self._on_edit)
        self.txt.bind("<ButtonRelease>", self._update_pos)
        self.txt.bind("<Control-s>",     lambda e: (self.save_file(), "break")[1])
        self.txt.bind("<Control-S>",     lambda e: (self.save_file_as(), "break")[1])
        self.txt.bind("<Control-f>",     lambda e: (self._toggle_find(False),"break")[1])
        self.txt.bind("<Control-h>",     lambda e: (self._toggle_find(True), "break")[1])
        self.txt.bind("<Control-g>",     lambda e: (self._goto_dialog(), "break")[1])
        self.txt.bind("<F3>",            lambda e: (self._find_next(), "break")[1])
        self.txt.bind("<Escape>",        lambda e: self._dismiss_popup_or_find())
        self.txt.bind("<Return>",        self._auto_indent)
        self.txt.bind("<Tab>",           self._on_tab)

        # ping AI at startup
        self._ai.ping_async(self._on_ping)

    def _build_findbar(self):
        f = self._fr
        tk.Label(f, text="Cerca:", font=FONT_SMALL, bg=C["bg3"],
                 fg=C["text_dim"]).pack(side="left", padx=(8,2), pady=5)
        self._fv = tk.StringVar()
        fe = tk.Entry(f, textvariable=self._fv, font=FONT_MONO,
                      bg=C["bg"], fg=C["text"], insertbackground=C["text"],
                      relief="flat", bd=4, width=22)
        fe.pack(side="left", pady=5)
        fe.bind("<Return>",       lambda _: self._find_next())
        fe.bind("<KP_Enter>",     lambda _: self._find_next())
        fe.bind("<Shift-Return>", lambda _: self._find_prev())
        self._fe = fe
        for lbl, cmd in [("▼", self._find_next),("▲", self._find_prev)]:
            _Btn(f, lbl, cmd).pack(side="left", padx=1, pady=5)
        self._mlbl = tk.Label(f, text="", font=FONT_SMALL,
                              bg=C["bg3"], fg=C["text_dim"])
        self._mlbl.pack(side="left", padx=4)
        self._rep_frame = tk.Frame(f, bg=C["bg3"])
        self._rep_frame.pack(side="left")
        tk.Label(self._rep_frame, text="Sostituisci:", font=FONT_SMALL,
                 bg=C["bg3"], fg=C["text_dim"]).pack(side="left", padx=(8,2))
        self._rv = tk.StringVar()
        tk.Entry(self._rep_frame, textvariable=self._rv, font=FONT_MONO,
                 bg=C["bg"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", bd=4, width=22).pack(side="left")
        for lbl, cmd in [("Sost.", self._rep_one),("Tutti", self._rep_all)]:
            _Btn(self._rep_frame, lbl, cmd).pack(side="left", padx=2)
        self._ci = tk.IntVar(value=1)
        tk.Checkbutton(f, text="Aa", variable=self._ci, bg=C["bg3"],
                       fg=C["text_dim"], selectcolor=C["bg3"],
                       activebackground=C["bg3"],
                       font=FONT_SMALL).pack(side="left", padx=4)
        _Btn(f, "✕", self._hide_find).pack(side="right", padx=8, pady=5)

    # ── AI status ──────────────────────────────────────────────────────────────
    def _on_ping(self, ok: bool):
        self.after(0, lambda: self._ai_dot.config(
            fg=C["success"] if ok else C["error"],
            text="●"))
        if not ok:
            self.after(0, lambda: self._ai_dot.config(
                text="● offline"))

    def refresh_ai_status(self):
        self._ai_dot.config(fg=C["ai_dim"], text="●…")
        self._ai.ping_async(self._on_ping)

    # ── autocomplete ──────────────────────────────────────────────────────────
    def _on_edit(self, event=None):
        self._sched_hl()
        self._update_ln()
        self._update_pos()
        self._update_curline()
        if not self._dirty:
            self._set_dirty(True)
        # dismiss popup on edit
        if self._popup:
            try: self._popup.destroy()
            except Exception: pass
            self._popup = None
        # schedule autocomplete
        key = getattr(event, "keysym", "") if event else ""
        if (self._ai.ac_enabled
                and self._ai.status == AIClient.STATUS_OK
                and key not in _NO_AC_KEYS):
            self._sched_ac()

    def _sched_ac(self):
        if self._ac_job: self.after_cancel(self._ac_job)
        self._ac_job = self.after(self._ai.ac_delay, self._trigger_ac)

    def _trigger_ac(self):
        self._ac_job = None
        if not self._ai.ac_enabled or self._ai.status != AIClient.STATUS_OK:
            return
        # get context: last 40 lines up to cursor
        cur = self.txt.index("insert")
        ln  = int(cur.split(".")[0])
        start_ln = max(1, ln - 40)
        before = self.txt.get(f"{start_ln}.0", "insert")
        if len(before.strip()) < 5:
            return

        def on_result(items):
            if not items or not self.winfo_exists():
                return
            self.after(0, lambda: self._show_popup(items))

        self._ai.autocomplete(before, on_result)

    def _show_popup(self, items: list):
        if self._popup:
            try: self._popup.destroy()
            except Exception: pass
        # get cursor screen position
        bbox = self.txt.bbox("insert")
        if not bbox:
            return
        x, y, _, h = bbox
        sx = self.txt.winfo_rootx() + x
        sy = self.txt.winfo_rooty() + y + h + 2

        def on_accept(text: str):
            self._popup = None
            self.txt.insert("insert", text)
            self._sched_hl()
            self._set_dirty(True)

        def on_dismiss():
            self._popup = None

        self._popup = CompletionPopup(self, items, on_accept, on_dismiss)
        self._popup.position(sx, sy)

    def _on_tab(self, event=None):
        # if popup active, let Tab accept it
        if self._popup:
            return  # popup handles Tab itself
        self.txt.insert("insert", "  ")
        return "break"

    def _dismiss_popup_or_find(self):
        if self._popup:
            try: self._popup.destroy()
            except Exception: pass
            self._popup = None
        elif self._find_open:
            self._hide_find()

    # ── AI check ──────────────────────────────────────────────────────────────
    def _ai_check_btn(self):
        if self._ai.status == AIClient.STATUS_OFFLINE:
            messagebox.showwarning(
                "AI non disponibile",
                f"Impossibile raggiungere {self._ai.endpoint}.\n"
                "Avvia Ollama o modifica l'endpoint in Impostazioni.")
            return
        content = self.get_content()
        if not content.strip():
            return
        # open AI panel and show loading
        if not self._ai_panel_open:
            self._toggle_ai_panel()
        self._ai_panel._append("✨ Check", "Analisi in corso…\n", "thinking")
        self.clear_errors()

        raw_buf = [""]

        def on_token(tok):
            if not self.winfo_exists():
                return
            raw_buf[0] += tok
            # stream tokens live into the AI panel
            self.after(0, lambda t=tok: self._ai_panel.chat_txt.config(state="normal") or
                       self._ai_panel.chat_txt.insert("end", t, "assistant") or
                       self._ai_panel.chat_txt.see("end") or
                       self._ai_panel.chat_txt.config(state="disabled"))

        def on_done(raw: str):
            if not self.winfo_exists():
                return
            issues = self._parse_ai_issues(raw)
            self.after(0, lambda: self._finalize_check(raw, issues))

        self._ai.check_xslt(content, on_token, on_done)

    def _parse_ai_issues(self, raw: str) -> list:
        """Parse 'LINE n: [SEVERITY] desc' lines from AI response."""
        issues = []
        for m in re.finditer(r'LINE\s+(\d+)\s*:\s*\[(ERROR|WARNING|INFO)\]\s*(.+)',
                             raw, re.I):
            issues.append((int(m.group(1)),
                           m.group(2).upper(),
                           m.group(3).strip()))
        return issues

    def _finalize_check(self, raw: str, issues: list):
        """Called when streaming check is complete."""
        # clear the inline streamed text (it was shown token-by-token already)
        self._ai_panel.chat_txt.config(state="normal")
        try:
            idx = self._ai_panel.chat_txt.search("✨ Check", "1.0", "end")
            if idx:
                end_idx = self._ai_panel.chat_txt.index(f"{idx} lineend +1c")
                # find next "AI " line start after that
                self._ai_panel.chat_txt.delete(end_idx,
                    self._ai_panel.chat_txt.index("end-1c"))
        except Exception:
            pass
        self._ai_panel.chat_txt.config(state="disabled")
        self._apply_ai_issues(raw, issues)

    def _apply_ai_issues(self, raw: str, issues: list):
        # clear old markers
        self.txt.tag_remove("err_line",  "1.0", "end")
        self.txt.tag_remove("warn_line", "1.0", "end")
        self.gutter.config(state="normal")
        self.gutter.tag_remove("err_g",  "1.0", "end")
        self.gutter.tag_remove("warn_g", "1.0", "end")
        self._err_lines = []

        for (ln, sev, _desc) in issues:
            if sev == "ERROR":
                self.txt.tag_add("err_line",  f"{ln}.0", f"{ln}.end+1c")
                self.gutter.tag_add("err_g",  f"{ln}.0", f"{ln}.end+1c")
                self._err_lines.append(ln)
            elif sev == "WARNING":
                self.txt.tag_add("warn_line", f"{ln}.0", f"{ln}.end+1c")
                self.gutter.tag_add("warn_g", f"{ln}.0", f"{ln}.end+1c")
        self.gutter.config(state="disabled")

        self._ai_panel.show_check_result(raw, issues)
        if issues and self._err_lines:
            self.txt.see(f"{self._err_lines[0]}.0")

    # ── AI panel toggle ───────────────────────────────────────────────────────
    def _toggle_ai_panel(self):
        if self._ai_panel_open:
            self._vpane.forget(self._ai_panel)
            self._ai_panel_open = False
            self._chat_btn.config(text="🤖 Chat AI")
        else:
            self._vpane.add(self._ai_panel, weight=1)
            self._ai_panel_open = True
            self._chat_btn.config(text="🤖 Chat ✕")
            self._ai_panel._update_model_label()
            self._ai_panel.focus_input()

    # ── scrolling ──────────────────────────────────────────────────────────────
    def _yscroll(self, *a):
        self.txt.yview(*a); self._sync_gutter()

    def _sync_gutter(self):
        self.gutter.yview_moveto(self.txt.yview()[0])

    # ── file ops ──────────────────────────────────────────────────────────────
    def load_file(self, path: str, reload: bool = False) -> bool:
        if not reload and self._dirty:
            ans = messagebox.askyesnocancel(
                "Modifiche non salvate",
                f"Salvare {os.path.basename(self._filepath or 'file corrente')}?")
            if ans is None: return False
            if ans: self.save_file()
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as ex:
            messagebox.showerror("Errore apertura", str(ex)); return False
        self.txt.delete("1.0","end")
        self.txt.insert("1.0", content)
        self._filepath = path
        self._set_dirty(False)
        self._err_lines = []
        self._update_ln()
        self._sched_hl(80)
        self._update_title()
        return True

    def open_dialog(self):
        p = filedialog.askopenfilename(
            title="Apri XSLT/XML",
            filetypes=[("XSLT","*.xsl *.xslt"),("XML","*.xml"),("All","*.*")])
        if p: self.load_file(p)

    def save_file(self) -> bool:
        if not self._filepath: return self.save_file_as()
        try:
            with open(self._filepath,"w",encoding="utf-8") as f:
                f.write(self.txt.get("1.0","end-1c"))
            self._set_dirty(False)
            if self._on_save: self._on_save(self._filepath)
            return True
        except Exception as ex:
            messagebox.showerror("Errore salvataggio", str(ex)); return False

    def save_file_as(self) -> bool:
        p = filedialog.asksaveasfilename(
            title="Salva con nome", defaultextension=".xsl",
            filetypes=[("XSLT","*.xsl *.xslt"),("XML","*.xml"),("All","*.*")])
        if not p: return False
        self._filepath = p
        self._update_title()
        return self.save_file()

    def get_filepath(self): return self._filepath
    def get_content(self) -> str: return self.txt.get("1.0","end-1c")

    def _set_dirty(self, flag):
        self._dirty = flag
        self._dirty_lbl.config(text="● non salvato" if flag else "")
        if self._on_dirty: self._on_dirty(flag)

    def _update_title(self):
        if self._filepath:
            self._title_lbl.config(text=os.path.basename(self._filepath),
                                   fg=C["accent"])
        else:
            self._title_lbl.config(text="Nessun file", fg=C["text_dim"])

    # ── goto ──────────────────────────────────────────────────────────────────
    def goto_line(self, n: int, col: int = 0):
        total = int(self.txt.index("end-1c").split(".")[0])
        n = max(1, min(n, total))
        self.txt.mark_set("insert", f"{n}.{col}")
        self.txt.see(f"{n}.{col}")
        self.txt.tag_remove("curline","1.0","end")
        self.txt.tag_add("curline", f"{n}.0", f"{n}.end+1c")
        self._update_pos()

    def _goto_dialog(self):
        total = int(self.txt.index("end-1c").split(".")[0])
        ans = simpledialog.askinteger(
            "Vai a riga", f"Numero riga (1–{total}):",
            parent=self, minvalue=1, maxvalue=total)
        if ans:
            self.goto_line(ans); self.txt.focus_set()

    # ── error markers ─────────────────────────────────────────────────────────
    def mark_error_lines(self, lines: list):
        self.txt.tag_remove("err_line","1.0","end")
        self.gutter.config(state="normal")
        self.gutter.tag_remove("err_g","1.0","end")
        self._err_lines = lines
        for n in lines:
            self.txt.tag_add("err_line",f"{n}.0",f"{n}.end+1c")
            self.gutter.tag_add("err_g",f"{n}.0",f"{n}.end+1c")
        self.gutter.config(state="disabled")
        self.txt.tag_raise("err_line")

    def clear_errors(self):
        self.mark_error_lines([])
        self.txt.tag_remove("warn_line","1.0","end")
        self.gutter.config(state="normal")
        self.gutter.tag_remove("warn_g","1.0","end")
        self.gutter.config(state="disabled")

    # ── syntax highlighting ────────────────────────────────────────────────────
    def _sched_hl(self, delay=260):
        if self._hl_job: self.after_cancel(self._hl_job)
        self._hl_job = self.after(delay, self._highlight)

    def _highlight(self):
        self._hl_job = None
        content = self.txt.get("1.0","end")
        for tag,_ in _XSLT_HL: self.txt.tag_remove(tag,"1.0","end")
        for tag,pat in _XSLT_HL:
            for m in pat.finditer(content):
                ts = self._off(content, m.start())
                te = self._off(content, m.end())
                self.txt.tag_add(tag, ts, te)
        self.mark_error_lines(self._err_lines)

    @staticmethod
    def _off(text, offset) -> str:
        before = text[:offset]
        line = before.count('\n') + 1
        col  = len(before) - before.rfind('\n') - 1
        return f"{line}.{col}"

    # ── line numbers ───────────────────────────────────────────────────────────
    def _update_ln(self):
        count = int(self.txt.index("end-1c").split(".")[0])
        self.gutter.config(state="normal")
        self.gutter.delete("1.0","end")
        self.gutter.insert("1.0","\n".join(str(i) for i in range(1,count+1)))
        for n in self._err_lines:
            self.gutter.tag_add("err_g",f"{n}.0",f"{n}.end+1c")
        self.gutter.config(state="disabled")

    def _update_pos(self, event=None):
        idx = self.txt.index("insert"); ln,col = idx.split(".")
        self._pos_lbl.config(text=f"Ln {ln}  Col {int(col)+1}")

    def _update_curline(self):
        self.txt.tag_remove("curline","1.0","end")
        ln = self.txt.index("insert").split(".")[0]
        self.txt.tag_add("curline",f"{ln}.0",f"{ln}.end+1c")
        self.txt.tag_raise("err_line")

    # ── auto-indent ────────────────────────────────────────────────────────────
    def _auto_indent(self, event=None):
        line   = self.txt.get("insert linestart","insert")
        indent = re.match(r'^(\s*)', line).group(1)
        stripped = line.rstrip()
        if stripped.endswith('>') and not stripped.endswith('/>') \
                and not stripped.startswith('</'):
            indent += '  '
        self.txt.insert("insert","\n"+indent)
        self.txt.see("insert")
        return "break"

    # ── find / replace ─────────────────────────────────────────────────────────
    def _toggle_find(self, replace):
        if self._find_open and not replace:
            self._hide_find(); return
        if not self._find_open:
            self._fr.pack(fill="x", before=self._vpane)
            self._find_open = True
        if replace: self._rep_frame.pack(side="left")
        else:       self._rep_frame.pack_forget()
        try:
            sel = self.txt.get("sel.first","sel.last")
            if '\n' not in sel and len(sel)<60:
                self._fv.set(sel); self._fe.select_range(0,"end")
        except tk.TclError: pass
        self._fe.focus_set()

    def _hide_find(self):
        self._fr.pack_forget(); self._find_open = False
        self.txt.tag_remove("hl_find","1.0","end")
        self.txt.tag_remove("hl_find_cur","1.0","end")
        self._mlbl.config(text=""); self.txt.focus_set()

    def _do_search(self):
        q = self._fv.get()
        if not q: return []
        self.txt.tag_remove("hl_find","1.0","end")
        self.txt.tag_remove("hl_find_cur","1.0","end")
        nocase = bool(self._ci.get())
        positions = []
        start = "1.0"
        while True:
            pos = self.txt.search(q, start,"end",nocase=nocase)
            if not pos: break
            end = f"{pos}+{len(q)}c"
            self.txt.tag_add("hl_find",pos,end)
            positions.append((pos,end)); start=end
        self._find_pos = positions; return positions

    def _find_next(self):
        pos = self._do_search()
        if not pos: self._mlbl.config(text="Nessun risultato",fg=C["error"]); return
        self._find_cur=(self._find_cur+1)%len(pos); self._jump()

    def _find_prev(self):
        pos = self._do_search()
        if not pos: return
        self._find_cur=(self._find_cur-1)%len(pos); self._jump()

    def _jump(self):
        if not self._find_pos: return
        p,e = self._find_pos[self._find_cur]
        self.txt.tag_remove("hl_find_cur","1.0","end")
        self.txt.tag_add("hl_find_cur",p,e)
        self.txt.see(p)
        self._mlbl.config(text=f"{self._find_cur+1}/{len(self._find_pos)}",
                          fg=C["success"])

    def _rep_one(self):
        if not self._do_search() or self._find_cur<0: self._find_next(); return
        if self._find_cur>=len(self._find_pos): return
        p,e=self._find_pos[self._find_cur]
        self.txt.delete(p,e); self.txt.insert(p,self._rv.get())
        self._set_dirty(True); self._find_next()

    def _rep_all(self):
        pos=self._do_search()
        if not pos: return
        for p,e in reversed(pos):
            self.txt.delete(p,e); self.txt.insert(p,self._rv.get())
        self._set_dirty(True); self._sched_hl()
        self._mlbl.config(text=f"Sostituiti {len(pos)}",fg=C["success"])


# ============================================================================
# OutputPanel
# ============================================================================
class OutputPanel(tk.Frame):
    def __init__(self, parent, title: str, **kw):
        super().__init__(parent, bg=C["bg2"], **kw)
        self._title     = title
        self._positions: list = []
        self._cur_idx   = -1
        self._link_data: dict = {}
        self._err_idx: list   = []
        self._err_cur   = -1
        self._navigate_cb     = None
        self._build()

    def set_navigate_callback(self, cb): self._navigate_cb = cb

    def _build(self):
        self._sumbar = tk.Frame(self, bg=C["error_bg"])
        self._sum_lbl = tk.Label(self._sumbar, text="", font=FONT_UI_B,
                                 bg=C["error_bg"], fg=C["error"], anchor="w")
        self._sum_lbl.pack(side="left", padx=10, pady=4)
        for lbl,cmd in [("▲ Prec.",self._prev_err),("▼ Succ.",self._next_err)]:
            _Btn(self._sumbar,lbl,cmd).pack(side="left",padx=2,pady=3)
        self._hint_lbl=tk.Label(self._sumbar,text="",font=FONT_SMALL,
                                bg=C["error_bg"],fg=C["warning"],
                                wraplength=500,justify="left")
        self._hint_lbl.pack(side="left",padx=10)

        tb=tk.Frame(self,bg=C["bg3"]); tb.pack(fill="x")
        tk.Label(tb,text=self._title,font=FONT_UI_B,
                 bg=C["bg3"],fg=C["accent"]).pack(side="left",padx=10,pady=6)
        tk.Label(tb,text="Cerca:",font=FONT_SMALL,
                 bg=C["bg3"],fg=C["text_dim"]).pack(side="left",padx=(16,2))
        self._sv=tk.StringVar()
        se=tk.Entry(tb,textvariable=self._sv,font=FONT_MONO,
                    bg=C["bg"],fg=C["text"],insertbackground=C["text"],
                    relief="flat",bd=4,width=22)
        se.pack(side="left")
        se.bind("<Return>",   lambda _:self._find("next"))
        se.bind("<KP_Enter>", lambda _:self._find("next"))
        for lbl,cmd in [("▼",lambda:self._find("next")),("▲",lambda:self._find("prev"))]:
            _Btn(tb,lbl,cmd).pack(side="left",padx=1)
        self._mlbl=tk.Label(tb,text="",font=FONT_SMALL,bg=C["bg3"],fg=C["text_dim"])
        self._mlbl.pack(side="left",padx=4)
        _Btn(tb,"Clear",self._clear_hl).pack(side="left",padx=4)
        _Btn(tb,"💾 Salva",self._save,accent=True).pack(side="right",padx=6)
        _Btn(tb,"🗑 Pulisci",self.clear).pack(side="right",padx=2)

        tf=tk.Frame(self,bg=C["bg2"]); tf.pack(fill="both",expand=True)
        self.txt=tk.Text(tf,wrap="none",font=FONT_MONO,
                         bg=C["panel"],fg=C["text"],
                         insertbackground=C["text"],
                         selectbackground=C["accent"],selectforeground=C["bg"],
                         relief="flat",bd=0,state="disabled")
        ys=tk.Scrollbar(tf,bg=C["bg2"],command=self.txt.yview)
        xs=tk.Scrollbar(tf,orient="horizontal",bg=C["bg2"],command=self.txt.xview)
        self.txt.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        xs.pack(side="bottom",fill="x"); ys.pack(side="right",fill="y")
        self.txt.pack(side="left",fill="both",expand=True)
        self.txt.tag_configure("error",   foreground=C["error"],  font=FONT_MONO_B)
        self.txt.tag_configure("err_bg",  background=C["error_bg"])
        self.txt.tag_configure("warning", foreground=C["warning"])
        self.txt.tag_configure("location",foreground=C["accent2"])
        self.txt.tag_configure("info",    foreground=C["info"])
        self.txt.tag_configure("stack",   foreground=C["text_dim"])
        self.txt.tag_configure("hl",      background=C["search_hl"])
        self.txt.tag_configure("hl_cur",  background=C["search_cur"],foreground=C["bg"])
        self.txt.tag_configure("link",    foreground=C["accent"],underline=True)
        self.txt.tag_configure("code_hint",foreground=C["warning"],underline=True)

    def clear(self):
        self.txt.config(state="normal"); self.txt.delete("1.0","end")
        self.txt.config(state="disabled")
        self._positions=[]; self._cur_idx=-1
        self._link_data={}; self._err_idx=[]; self._err_cur=-1
        self._mlbl.config(text=""); self._sumbar.pack_forget()

    def set_text(self, content, apply_highlighting=False):
        self.txt.config(state="normal"); self.txt.delete("1.0","end")
        self._link_data={}; self._err_idx=[]
        if apply_highlighting:
            self._insert_hl(content); self._show_summary()
        else:
            self.txt.insert("end",content)
        self.txt.config(state="disabled"); self.txt.see("1.0")

    def append(self, text, tag=""):
        self.txt.config(state="normal")
        if tag: self.txt.insert("end",text,tag)
        else:   self.txt.insert("end",text)
        self.txt.config(state="disabled")

    def get_text(self): return self.txt.get("1.0","end")

    def _classify(self, line):
        ll=line.lower()
        if any(k in ll for k in ("fatal","error:","xpst","xpdy","xpty",
                                  "xtse","xtde","sxxp","exception:")):
            return "error"
        if "error" in ll or "failed" in ll: return "error"
        if "warning" in ll or "warn:" in ll: return "warning"
        if any(k in ll for k in ("on line ","column ","in module","in file","at line ")):
            return "location"
        if ll.strip().startswith("at ") and "(" in ll: return "stack"
        if any(k in ll for k in ("info","loaded","timing","version")): return "info"
        return ""

    def _insert_hl(self, content):
        link_c=[0]
        def make_link(path,lineno):
            tag=f"lnk_{link_c[0]}"; link_c[0]+=1
            self._link_data[tag]=(path,lineno); return tag

        for line in content.split("\n"):
            ltag=self._classify(line)
            if ltag=="error":
                si=self.txt.index("end-1c")
                self.txt.insert("end",line+"\n",(ltag,"err_bg"))
                self._err_idx.append(self.txt.index(si))
            elif ltag: self.txt.insert("end",line+"\n",ltag)
            else:      self.txt.insert("end",line+"\n")

            for m in _CODE_RE.finditer(line):
                code=m.group(1).upper()
                if code in SUGGESTIONS:
                    ln=int(self.txt.index("end-1c").split(".")[0])-1
                    ps,pe=f"{ln}.{m.start()}",f"{ln}.{m.end()}"
                    htag=f"code_{code}_{ln}"
                    self.txt.tag_add("code_hint",ps,pe)
                    self.txt.tag_add(htag,ps,pe)
                    sug=SUGGESTIONS[code]
                    self.txt.tag_bind(htag,"<Button-1>",
                                      lambda e,s=sug: self._show_hint(s))
                    self.txt.tag_bind(htag,"<Enter>",
                                      lambda e: self.txt.config(cursor="hand2"))
                    self.txt.tag_bind(htag,"<Leave>",
                                      lambda e: self.txt.config(cursor=""))

            for m in _LOC_RE.finditer(line):
                ls,rp=m.group(1),m.group(3)
                if ls and rp:
                    lineno=int(ls); path=self._clean(rp)
                    cl=int(self.txt.index("end-1c").split(".")[0])-1
                    lnk=make_link(path,lineno)
                    ps,pe=f"{cl}.{m.start()}",f"{cl}.{m.end()}"
                    self.txt.tag_add("link",ps,pe); self.txt.tag_add(lnk,ps,pe)
                    self.txt.tag_bind(lnk,"<Button-1>",
                                      lambda e,p=path,n=lineno: self._on_link(p,n))
                    self.txt.tag_bind(lnk,"<Enter>",
                                      lambda e: self.txt.config(cursor="hand2"))
                    self.txt.tag_bind(lnk,"<Leave>",
                                      lambda e: self.txt.config(cursor=""))

    @staticmethod
    def _clean(raw):
        p=raw.strip().rstrip(':,')
        if p.startswith("file:///"): p=p[8:]
        elif p.startswith("file://"): p=p[7:]
        p=p.replace('/',os.sep)
        if not os.path.isabs(p): p=os.path.abspath(p)
        return p

    def _on_link(self,path,lineno):
        if self._navigate_cb: self._navigate_cb(path,lineno)

    def _show_hint(self,suggestion):
        t,b=suggestion
        self._sumbar.pack(fill="x",before=self.txt.master)
        self._sum_lbl.config(text=f"💡 {t}")
        self._hint_lbl.config(text=b)

    def _show_summary(self):
        content=self.txt.get("1.0","end")
        ne=len(re.findall(r'^(Error|XPST|XPDY|XPTY|XTSE|XTDE|SXXP)',content,re.M|re.I))
        nw=len(re.findall(r'^Warning',content,re.M|re.I))
        if ne==0 and nw==0: self._sumbar.pack_forget(); return
        parts=[]
        if ne: parts.append(f"❌ {ne} error{'i' if ne>1 else 'e'}")
        if nw: parts.append(f"⚠️ {nw} warning")
        self._sum_lbl.config(text="  ".join(parts))
        self._hint_lbl.config(
            text="Clicca codice errore (es. XPST0003) per suggerimenti. "
                 "Clicca posizione file per aprirla nell'editor.")
        self._sumbar.pack(fill="x",before=self.txt.master)

    def _prev_err(self):
        if not self._err_idx: return
        self._err_cur=(self._err_cur-1)%len(self._err_idx)
        self.txt.see(self._err_idx[self._err_cur])

    def _next_err(self):
        if not self._err_idx: return
        self._err_cur=(self._err_cur+1)%len(self._err_idx)
        self.txt.see(self._err_idx[self._err_cur])

    def _find(self,direction):
        q=self._sv.get()
        if not q: return
        self.txt.tag_remove("hl","1.0","end"); self.txt.tag_remove("hl_cur","1.0","end")
        positions=[]; start="1.0"
        while True:
            pos=self.txt.search(q,start,"end",nocase=True)
            if not pos: break
            end=f"{pos}+{len(q)}c"
            self.txt.tag_add("hl",pos,end); positions.append((pos,end)); start=end
        self._positions=positions
        if not positions: self._mlbl.config(text="Nessun risultato",fg=C["error"]); return
        self._cur_idx=((self._cur_idx+1)if direction=="next"
                       else(self._cur_idx-1))%len(positions)
        p,e=positions[self._cur_idx]
        self.txt.tag_remove("hl_cur","1.0","end"); self.txt.tag_add("hl_cur",p,e)
        self.txt.see(p); self._mlbl.config(text=f"{self._cur_idx+1}/{len(positions)}",fg=C["success"])

    def _clear_hl(self):
        self.txt.tag_remove("hl","1.0","end"); self.txt.tag_remove("hl_cur","1.0","end")
        self._mlbl.config(text="")

    def _save(self):
        content=self.txt.get("1.0","end")
        path=filedialog.asksaveasfilename(
            title="Salva output",defaultextension=".log",
            filetypes=[("Log","*.log"),("Text","*.txt"),("XML","*.xml"),("All","*.*")])
        if path:
            try:
                with open(path,"w",encoding="utf-8") as f: f.write(content)
                messagebox.showinfo("Salvato",f"Salvato in:\n{path}")
            except Exception as ex: messagebox.showerror("Errore",str(ex))


# ============================================================================
# SettingsDialog  (with AI tab)
# ============================================================================
class SettingsDialog:
    def __init__(self, parent, config: dict, on_save):
        self.config=config; self.on_save=on_save
        self.win=tk.Toplevel(parent)
        self.win.title("Impostazioni")
        self.win.geometry("720x500")
        self.win.configure(bg=C["bg"])
        self.win.transient(parent); self.win.grab_set()
        self._build()

    def _build(self):
        nb=ttk.Notebook(self.win); nb.pack(fill="both",expand=True,padx=10,pady=10)

        # ── Saxon tab ──
        st=tk.Frame(nb,bg=C["bg"]); nb.add(st,text="  Saxon JAR  ")
        ttk.Label(st,text="Percorsi JAR Saxon",font=FONT_UI_B,
                  background=C["bg"],foreground=C["accent"]).pack(anchor="w",padx=14,pady=(12,0))
        ttk.Label(st,text="Doppio clic per impostare come attivo.",
                  font=FONT_SMALL,background=C["bg"],foreground=C["text_dim"]).pack(
                      anchor="w",padx=14,pady=(0,6))
        lf=tk.Frame(st,bg=C["panel"],highlightbackground=C["border"],highlightthickness=1)
        lf.pack(fill="both",expand=True,padx=14,pady=4)
        sb=tk.Scrollbar(lf,bg=C["bg2"])
        self.lb=tk.Listbox(lf,yscrollcommand=sb.set,font=FONT_MONO,
                           bg=C["panel"],fg=C["text"],
                           selectbackground=C["accent"],selectforeground=C["bg"],
                           activestyle="none",borderwidth=0,highlightthickness=0,relief="flat")
        sb.config(command=self.lb.yview)
        self.lb.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        self.lb.bind("<Double-Button-1>",lambda _:self._set_active())
        self._refresh()
        self.active_lbl=ttk.Label(st,text="",font=FONT_SMALL,
                                  background=C["bg"],foreground=C["success"])
        self.active_lbl.pack(anchor="w",padx=14); self._upd_lbl()
        bf=tk.Frame(st,bg=C["bg"]); bf.pack(fill="x",padx=14,pady=6)
        for txt,cmd in [("Aggiungi JAR…",self._add),("Rimuovi",self._remove),
                        ("Imposta attivo ✓",self._set_active),
                        ("Su ↑",self._up),("Giù ↓",self._dn)]:
            _Btn(bf,txt,cmd).pack(side="left",padx=3)

        # ── AI tab ──
        at=tk.Frame(nb,bg=C["bg"]); nb.add(at,text="  🤖 AI Locale  ")
        body=tk.Frame(at,bg=C["bg"]); body.pack(fill="both",padx=18,pady=14,expand=True)

        def lrow(lbl,var,width=40):
            tk.Label(body,text=lbl,font=FONT_SMALL,bg=C["bg"],
                     fg=C["text_dim"]).pack(anchor="w",pady=(8,0))
            e=tk.Entry(body,textvariable=var,font=FONT_MONO,
                       bg=C["bg3"],fg=C["text"],insertbackground=C["text"],
                       relief="flat",bd=4,width=width)
            e.pack(anchor="w"); return e

        self._v_ep   = tk.StringVar(value=self.config.get("ai_endpoint","http://localhost:11434"))
        self._v_mdl  = tk.StringVar(value=self.config.get("ai_model","mistral"))
        self._v_dly  = tk.StringVar(value=str(self.config.get("ai_ac_delay",700)))
        self._v_aien = tk.IntVar(value=int(self.config.get("ai_enabled",1)))
        self._v_acen = tk.IntVar(value=int(self.config.get("ai_autocomplete",1)))

        lrow("Endpoint AI (Ollama/LM Studio)",self._v_ep)
        tk.Label(body,
                 text="Ollama: http://localhost:11434   |   LM Studio: http://localhost:1234",
                 font=FONT_SMALL,bg=C["bg"],fg=C["text_dim"]).pack(anchor="w")
        lrow("Modello (es. mistral, qwen2.5-coder, llama3, phi3)",self._v_mdl)

        fr2=tk.Frame(body,bg=C["bg"]); fr2.pack(anchor="w",pady=(12,4))
        tk.Checkbutton(fr2,text="Abilita funzionalità AI",variable=self._v_aien,
                       bg=C["bg"],fg=C["text"],selectcolor=C["bg3"],
                       activebackground=C["bg"],font=FONT_UI).pack(side="left",padx=(0,20))
        tk.Checkbutton(fr2,text="Autocompletamento mentre scrivi",variable=self._v_acen,
                       bg=C["bg"],fg=C["text"],selectcolor=C["bg3"],
                       activebackground=C["bg"],font=FONT_UI).pack(side="left")

        lrow("Ritardo autocompletamento (ms, default 700)",self._v_dly,width=10)

        # connection test
        tr=tk.Frame(body,bg=C["bg"]); tr.pack(anchor="w",pady=(16,4))
        self._test_lbl=tk.Label(tr,text="",font=FONT_UI_B,bg=C["bg"],fg=C["text_dim"])
        def test_conn():
            ep=self._v_ep.get().strip()
            mdl=self._v_mdl.get().strip()
            self._test_lbl.config(text="Connessione in corso…",fg=C["warning"])
            def worker():
                tmp=AIClient({"ai_endpoint":ep,"ai_model":mdl,"ai_enabled":True})
                ok=tmp.ping()
                self.win.after(0,lambda: self._test_lbl.config(
                    text=f"✅ Connesso a {ep}" if ok else f"❌ Impossibile raggiungere {ep}",
                    fg=C["success"] if ok else C["error"]))
            threading.Thread(target=worker,daemon=True).start()
        _Btn(tr,"🔌 Testa connessione",test_conn).pack(side="left")
        self._test_lbl.pack(side="left",padx=12)

        tk.Label(body,
                 text="Modelli consigliati per XSLT: qwen2.5-coder:7b  ·  mistral  ·  deepseek-coder-v2\n"
                      "Per installare: ollama pull mistral",
                 font=FONT_SMALL,bg=C["bg"],fg=C["text_dim"],justify="left").pack(
                     anchor="w",pady=(10,0))

        # ── ok/cancel ──
        tk.Frame(self.win,bg=C["border"],height=1).pack(fill="x",pady=(4,0))
        okf=tk.Frame(self.win,bg=C["bg"]); okf.pack(fill="x",padx=14,pady=8)
        _Btn(okf,"Annulla",self.win.destroy).pack(side="right",padx=3)
        _Btn(okf,"  OK  ",self._ok,accent=True).pack(side="right",padx=3)

    def _refresh(self):
        active=self.config.get("active_saxon","")
        self.lb.delete(0,"end")
        for p in self.config.get("saxon_paths",[]):
            self.lb.insert("end",f"{'● ' if p==active else '  '}{p}")
            if p==active: self.lb.itemconfig("end",fg=C["success"])

    def _upd_lbl(self):
        a=self.config.get("active_saxon","")
        self.active_lbl.config(text=f"Attivo: {a}" if a else "Nessun JAR impostato.")

    def _paths(self): return self.config.setdefault("saxon_paths",[])

    def _add(self):
        p=filedialog.askopenfilename(title="Seleziona JAR Saxon",parent=self.win,
                                     filetypes=[("JAR","*.jar"),("All","*.*")])
        if p and p not in self._paths():
            self._paths().append(p)
            if not self.config.get("active_saxon"): self.config["active_saxon"]=p
            self._refresh(); self._upd_lbl()

    def _remove(self):
        sel=self.lb.curselection()
        if not sel: return
        ps=self._paths(); removed=ps.pop(sel[0])
        if self.config.get("active_saxon")==removed:
            self.config["active_saxon"]=ps[0] if ps else ""
        self._refresh(); self._upd_lbl()

    def _set_active(self):
        sel=self.lb.curselection()
        if not sel: return
        ps=self._paths()
        if sel[0]<len(ps): self.config["active_saxon"]=ps[sel[0]]
        self._refresh(); self._upd_lbl()

    def _up(self):
        sel=self.lb.curselection()
        if not sel or sel[0]==0: return
        i=sel[0]; ps=self._paths(); ps[i-1],ps[i]=ps[i],ps[i-1]
        self._refresh(); self.lb.selection_set(i-1)

    def _dn(self):
        sel=self.lb.curselection(); ps=self._paths()
        if not sel or sel[0]>=len(ps)-1: return
        i=sel[0]; ps[i],ps[i+1]=ps[i+1],ps[i]
        self._refresh(); self.lb.selection_set(i+1)

    def _ok(self):
        self.config["ai_endpoint"]     = self._v_ep.get().strip()
        self.config["ai_model"]        = self._v_mdl.get().strip()
        self.config["ai_enabled"]      = bool(self._v_aien.get())
        self.config["ai_autocomplete"] = bool(self._v_acen.get())
        try:
            self.config["ai_ac_delay"] = max(300, int(self._v_dly.get()))
        except ValueError:
            self.config["ai_ac_delay"] = 700
        self.on_save(); self.win.destroy()


# ============================================================================
# SaxonRunner  (main app)
# ============================================================================
class SaxonRunner:
    def __init__(self, root: tk.Tk):
        self.root    = root
        self.process = None
        self.config  = self._load_cfg()
        self._current_file = None
        self._watcher = FileWatcher(self._on_file_changed)
        self._ai      = AIClient(self.config)

        root.title("Saxon XSLT Runner  v3.0")
        root.geometry("1440x880")
        root.minsize(1024,660)
        root.configure(bg=C["bg"])
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._style_ttk()
        self._build_menu()
        self._build_ui()
        self._refresh_recent()

    def _load_cfg(self):
        d={"saxon_paths":[],"active_saxon":"","recent":[],
           "ai_endpoint":"http://localhost:11434","ai_model":"mistral",
           "ai_enabled":True,"ai_autocomplete":True,"ai_ac_delay":700}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE,"r",encoding="utf-8") as f: d.update(json.load(f))
            except Exception: pass
        return d

    def _save_cfg(self):
        try:
            with open(CONFIG_FILE,"w",encoding="utf-8") as f:
                json.dump(self.config,f,indent=2,ensure_ascii=False)
        except Exception as ex: messagebox.showerror("Errore config",str(ex))

    def _style_ttk(self):
        s=ttk.Style()
        try: s.theme_use("clam")
        except Exception: pass
        s.configure(".",background=C["bg"],foreground=C["text"],
                    font=FONT_UI,borderwidth=0,relief="flat")
        s.configure("TLabel",background=C["bg"],foreground=C["text"])
        s.configure("TFrame",background=C["bg"])
        s.configure("TPanedwindow",background=C["border"])
        s.configure("TNotebook",background=C["bg"],tabmargins=[2,2,0,0])
        s.configure("TNotebook.Tab",background=C["bg3"],foreground=C["text_dim"],
                    padding=[12,5])
        s.map("TNotebook.Tab",
              background=[("selected",C["bg2"])],foreground=[("selected",C["accent"])])

    def _build_menu(self):
        mb=tk.Menu(self.root,bg=C["bg2"],fg=C["text"],
                   activebackground=C["btn_hover"],activeforeground=C["text"],
                   bd=0,relief="flat")
        self.root.config(menu=mb)
        def _m(lbl):
            m=tk.Menu(mb,tearoff=0,bg=C["bg2"],fg=C["text"],
                      activebackground=C["accent"],activeforeground=C["bg"],
                      bd=0,relief="flat")
            mb.add_cascade(label=lbl,menu=m); return m
        fm=_m("File")
        fm.add_command(label="Nuovo        Ctrl+N",command=self._new)
        fm.add_command(label="Apri…        Ctrl+O",command=self._open)
        fm.add_separator()
        fm.add_command(label="Salva        Ctrl+S",command=self._save)
        fm.add_command(label="Salva con nome…",    command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Esci",command=self._on_close)
        tm=_m("Strumenti")
        tm.add_command(label="Impostazioni…",command=self._open_settings)
        hm=_m("Help")
        hm.add_command(label="Informazioni…",command=self._about)
        self.root.bind("<Control-n>",lambda _:self._new())
        self.root.bind("<Control-o>",lambda _:self._open())
        self.root.bind("<Control-s>",lambda _:self._save())
        self.root.bind("<Control-S>",lambda _:self._save_as())

    def _build_ui(self):
        pane=ttk.PanedWindow(self.root,orient="horizontal")
        pane.pack(fill="both",expand=True)
        sidebar=tk.Frame(pane,bg=C["bg2"],width=330)
        sidebar.pack_propagate(False)
        pane.add(sidebar,weight=0)
        right=tk.Frame(pane,bg=C["bg"])
        pane.add(right,weight=1)
        self._build_sidebar(sidebar)
        self._build_output(right)

    def _build_sidebar(self,parent):
        hdr=tk.Frame(parent,bg=C["bg3"]); hdr.pack(fill="x")
        tk.Label(hdr,text="⚙  CONFIGURAZIONE",font=FONT_UI_B,
                 bg=C["bg3"],fg=C["accent"],pady=8,padx=12).pack(side="left")
        _Btn(hdr,"Impostazioni…",self._open_settings).pack(side="right",padx=8,pady=4)

        body=tk.Frame(parent,bg=C["bg2"]); body.pack(fill="x",padx=10,pady=6)

        def row(lbl,var,browse=None,readonly=False):
            tk.Label(body,text=lbl,font=FONT_SMALL,bg=C["bg2"],
                     fg=C["text_dim"]).pack(anchor="w",pady=(4,0))
            rf=tk.Frame(body,bg=C["bg2"]); rf.pack(fill="x")
            e=tk.Entry(rf,textvariable=var,font=FONT_MONO,
                       bg=C["bg3"],fg=C["text"],insertbackground=C["text"],
                       relief="flat",bd=4,
                       state="readonly" if readonly else "normal",
                       readonlybackground=C["bg3"])
            e.pack(side="left",fill="x",expand=True)
            if browse: _Btn(rf,"…",browse,width=3).pack(side="left",padx=(4,0))

        self._v_saxon  =tk.StringVar(value=self.config.get("active_saxon",""))
        self._v_xslt   =tk.StringVar()
        self._v_xml    =tk.StringVar()
        self._v_outdir =tk.StringVar(value=os.getcwd())
        self._v_outfile=tk.StringVar(value="output.log")
        self._v_confile=tk.StringVar(value="console.log")
        self._v_extra  =tk.StringVar()

        row("Saxon JAR (attivo)",    self._v_saxon,  readonly=True)
        row("Script XSLT",          self._v_xslt,   self._browse_xsl)
        row("XML sorgente",         self._v_xml,    self._browse_xml)
        tk.Frame(body,bg=C["border"],height=1).pack(fill="x",pady=6)
        row("Cartella output",      self._v_outdir, self._browse_outdir)
        row("File risultato",       self._v_outfile)
        row("File console log",     self._v_confile)
        row("Parametri extra Saxon",self._v_extra)

        self._v_xslt.trace_add("write",lambda *_:self._update_watcher())
        self._v_xml.trace_add( "write",lambda *_:self._update_watcher())

        tk.Frame(body,bg=C["border"],height=1).pack(fill="x",pady=8)
        br=tk.Frame(body,bg=C["bg2"]); br.pack(fill="x")
        self._run_btn  =_Btn(br,"▶  ESEGUI",self._run,run=True)
        self._stop_btn =_Btn(br,"■  STOP",  self._stop,stop=True,state="disabled")
        self._watch_btn=_Btn(br,"◯  Watch OFF",self._toggle_watch,width=14)
        self._run_btn.pack( side="left",fill="x",expand=True,padx=(0,2),ipady=3)
        self._stop_btn.pack(side="left",fill="x",expand=True,padx=(0,2),ipady=3)
        self._watch_btn.pack(side="left",fill="x",expand=True,ipady=3)

        self._status_var=tk.StringVar(value="Pronto")
        self._status_lbl=tk.Label(body,textvariable=self._status_var,
                                  font=FONT_SMALL,bg=C["bg2"],fg=C["text_dim"],
                                  anchor="w",wraplength=300,justify="left")
        self._status_lbl.pack(fill="x",pady=(6,0))

        tk.Frame(parent,bg=C["border"],height=1).pack(fill="x")
        rh=tk.Frame(parent,bg=C["bg3"]); rh.pack(fill="x")
        tk.Label(rh,text="🕐  RECENT RUNS",font=FONT_UI_B,
                 bg=C["bg3"],fg=C["accent"],pady=6,padx=12).pack(side="left")
        rbf=tk.Frame(rh,bg=C["bg3"]); rbf.pack(side="right",padx=6)
        for t,c in [("Carica",self._load_recent),("Elimina",self._del_recent),
                    ("Clear all",self._clear_recent)]:
            _Btn(rbf,t,c).pack(side="left",padx=2,pady=3)

        rf2=tk.Frame(parent,bg=C["panel"]); rf2.pack(fill="both",expand=True)
        sb=tk.Scrollbar(rf2,bg=C["bg3"])
        self._recent_lb=tk.Listbox(rf2,yscrollcommand=sb.set,font=FONT_SMALL,
                                   bg=C["panel"],fg=C["text"],
                                   selectbackground=C["accent"],selectforeground=C["bg"],
                                   activestyle="none",borderwidth=0,
                                   highlightthickness=0,relief="flat")
        sb.config(command=self._recent_lb.yview)
        self._recent_lb.pack(side="left",fill="both",expand=True)
        sb.pack(side="right",fill="y")
        self._recent_lb.bind("<Double-Button-1>",lambda _:self._load_recent())

    def _build_output(self,parent):
        nb=ttk.Notebook(parent); nb.pack(fill="both",expand=True)
        self._nb=nb
        self._out_panel=OutputPanel(nb,title="📄 Risultato (stdout)")
        nb.add(self._out_panel,text="  📄 Risultato  ")
        self._con_panel=OutputPanel(nb,title="🖥 Console / Errori (stderr)")
        nb.add(self._con_panel,text="  🖥 Console / Errori  ")
        self._editor=XSLTEditor(nb,self._ai,
                                on_save=self._on_editor_save,
                                on_dirty_change=self._on_editor_dirty)
        nb.add(self._editor,text="  ✏️ Editor XSLT  ")
        self._con_panel.set_navigate_callback(self._navigate_to)
        self._out_panel.set_navigate_callback(self._navigate_to)

    # ── browse ────────────────────────────────────────────────────────────────
    def _browse_xsl(self):
        p=filedialog.askopenfilename(title="Seleziona script XSLT",
                                     filetypes=[("XSLT","*.xsl *.xslt"),("All","*.*")])
        if p:
            self._v_xslt.set(p)
            ed=self._editor
            if ed.get_filepath() is None or ed.get_filepath()==p:
                ed.load_file(p,reload=(ed.get_filepath()==p))
            self._update_editor_tab()

    def _browse_xml(self):
        p=filedialog.askopenfilename(title="Seleziona XML sorgente",
                                     filetypes=[("XML/Text","*.xml *.txt"),("All","*.*")])
        if p: self._v_xml.set(p)

    def _browse_outdir(self):
        p=filedialog.askdirectory(title="Seleziona cartella output")
        if p: self._v_outdir.set(p)

    # ── run / stop ────────────────────────────────────────────────────────────
    def _collect_cmd(self):
        saxon=self.config.get("active_saxon","").strip()
        xslt=self._v_xslt.get().strip(); xml=self._v_xml.get().strip()
        if not saxon: raise ValueError("Saxon JAR non impostato.\nVai in Strumenti ▸ Impostazioni.")
        if not xslt:  raise ValueError("Seleziona uno script XSLT.")
        if not xml:   raise ValueError("Seleziona un file XML sorgente.")
        cmd=["java","-jar",saxon,f"-xsl:{xslt}",f"-s:{xml}"]
        extra=self._v_extra.get().strip()
        if extra: cmd+=extra.split()
        return cmd

    def _run(self):
        try: cmd=self._collect_cmd()
        except ValueError as ex:
            messagebox.showerror("Configurazione errata",str(ex)); return
        outdir=self._v_outdir.get() or os.getcwd()
        outfile=os.path.join(outdir,self._v_outfile.get() or "output.log")
        confile=os.path.join(outdir,self._v_confile.get() or "console.log")
        self._out_panel.clear(); self._con_panel.clear()
        self._editor.clear_errors()
        self._set_status("⏳ Esecuzione in corso…",C["warning"])
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._con_panel.append(f"▶  {' '.join(cmd)}\n\n","info")
        self._add_to_recent()

        def worker():
            try:
                proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                      text=True,encoding="utf-8",errors="replace",cwd=outdir)
                self.process=proc
                stdout,stderr=proc.communicate(); rc=proc.returncode
                try:
                    with open(outfile,"w",encoding="utf-8") as f: f.write(stdout)
                    with open(confile,"w",encoding="utf-8") as f: f.write(stderr)
                except Exception: pass
                err_lines=self._parse_err_lines(stderr)
                def ui():
                    self._out_panel.set_text(stdout)
                    self._con_panel.set_text(stderr,apply_highlighting=True)
                    if err_lines: self._editor.mark_error_lines(err_lines)
                    if rc==0:
                        self._set_status(f"✅ Completato (exit 0)  →  {outfile}",C["success"])
                    else:
                        self._set_status(f"❌ Errori (exit {rc})  →  vedi Console",C["error"])
                        self._nb.select(1)
                self.root.after(0,ui)
            except FileNotFoundError:
                self.root.after(0,lambda: messagebox.showerror(
                    "java non trovato","Installa JRE/JDK e assicurati che 'java' sia nel PATH."))
                self.root.after(0,lambda: self._set_status("❌ java non trovato",C["error"]))
            except Exception as ex:
                msg=str(ex)
                self.root.after(0,lambda: messagebox.showerror("Errore",msg))
                self.root.after(0,lambda: self._set_status(f"❌ {msg}",C["error"]))
            finally:
                self.process=None
                self.root.after(0,lambda: self._run_btn.config(state="normal"))
                self.root.after(0,lambda: self._stop_btn.config(state="disabled"))

        threading.Thread(target=worker,daemon=True).start()

    def _stop(self):
        if self.process: self.process.terminate()
        self._set_status("⛔ Interrotto",C["warning"])

    @staticmethod
    def _parse_err_lines(stderr):
        lines=set()
        for m in re.finditer(r'on line (\d+)(?:\s+column\s+\d+)?\s+of\s+\S+\.xsl[t]?',
                             stderr,re.I):
            lines.add(int(m.group(1)))
        return sorted(lines)

    def _set_status(self,msg,colour=""):
        self._status_var.set(msg)
        self._status_lbl.config(fg=colour or C["text_dim"])

    # ── watch ──────────────────────────────────────────────────────────────────
    def _toggle_watch(self):
        if self._watcher.active:
            self._watcher.stop()
            self._watch_btn.config(text="◯  Watch OFF",bg=C["watch_off"],fg=C["text"])
            self._set_status("Watch disattivato",C["text_dim"])
        else:
            self._watcher.set_files(self._v_xslt.get(),self._v_xml.get())
            self._watcher.start()
            self._watch_btn.config(text="⬤  Watch ON ",bg=C["watch_on"],fg=C["run_fg"])
            files=[os.path.basename(p) for p in [self._v_xslt.get(),self._v_xml.get()] if p]
            self._set_status(f"👁 Watch: {', '.join(files)}",C["watch_on"])

    def _update_watcher(self):
        if self._watcher.active:
            self._watcher.set_files(self._v_xslt.get(),self._v_xml.get())

    def _on_file_changed(self,path):
        fname=os.path.basename(path)
        def ui():
            self._set_status(f"🔄 Modifica rilevata: {fname} — riesecuzione…",C["warning"])
            ed=self._editor
            if ed.get_filepath()==path and not ed._dirty:
                ed.load_file(path,reload=True)
            self._run()
        self.root.after(0,ui)

    # ── editor integration ────────────────────────────────────────────────────
    def _navigate_to(self,path,lineno):
        self._nb.select(2)
        ed=self._editor
        if ed.get_filepath()!=path:
            if not ed.load_file(path): return
        ed.goto_line(lineno); ed.txt.focus_set()
        self._update_editor_tab()

    def _on_editor_save(self,path):
        if self._v_xslt.get()!=path: self._v_xslt.set(path)
        self._set_status(f"💾 Salvato: {os.path.basename(path)}",C["success"])
        self._update_editor_tab()

    def _on_editor_dirty(self,dirty): self._update_editor_tab()

    def _update_editor_tab(self):
        ed=self._editor; path=ed.get_filepath()
        name=os.path.basename(path) if path else "Editor XSLT"
        mark=" ●" if ed._dirty else ""
        try: self._nb.tab(2,text=f"  ✏️ {name}{mark}  ")
        except Exception: pass

    # ── recent ────────────────────────────────────────────────────────────────
    def _snapshot(self):
        return dict(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            saxon=self.config.get("active_saxon",""),
            xslt=self._v_xslt.get(),xml=self._v_xml.get(),
            outdir=self._v_outdir.get(),outfile=self._v_outfile.get(),
            confile=self._v_confile.get(),extra=self._v_extra.get(),
            label=(f"{os.path.basename(self._v_xslt.get())} ◂ "
                   f"{os.path.basename(self._v_xml.get())}"))

    def _add_to_recent(self):
        snap=self._snapshot(); recent=self.config.setdefault("recent",[])
        self.config["recent"]=[r for r in recent
                                if not(r.get("xslt")==snap["xslt"]
                                       and r.get("xml")==snap["xml"])]
        self.config["recent"].insert(0,snap)
        self.config["recent"]=self.config["recent"][:100]
        self._save_cfg(); self._refresh_recent()

    def _refresh_recent(self):
        self._recent_lb.delete(0,"end")
        for item in self.config.get("recent",[]):
            ts=item.get("timestamp","")[:16].replace("T"," ")
            self._recent_lb.insert("end",f"  {ts}   {item.get('label','—')}")

    def _sel_recent(self):
        sel=self._recent_lb.curselection(); return sel[0] if sel else None

    def _load_recent(self):
        idx=self._sel_recent()
        if idx is None: return
        recent=self.config.get("recent",[]); 
        if idx>=len(recent): return
        item=recent[idx]
        self._v_xslt.set(item.get("xslt",""));self._v_xml.set(item.get("xml",""))
        self._v_outdir.set(item.get("outdir","")); self._v_outfile.set(item.get("outfile","output.log"))
        self._v_confile.set(item.get("confile","console.log")); self._v_extra.set(item.get("extra",""))
        saxon=item.get("saxon","")
        if saxon and saxon in self.config.get("saxon_paths",[]):
            self.config["active_saxon"]=saxon; self._v_saxon.set(saxon)
        xslt=item.get("xslt","")
        if xslt and os.path.isfile(xslt):
            self._editor.load_file(xslt); self._update_editor_tab()

    def _del_recent(self):
        idx=self._sel_recent()
        if idx is None: return
        recent=self.config.get("recent",[])
        if idx<len(recent): del recent[idx]
        self._save_cfg(); self._refresh_recent()

    def _clear_recent(self):
        if messagebox.askyesno("Conferma","Rimuovere tutte le esecuzioni recenti?"):
            self.config["recent"]=[]; self._save_cfg(); self._refresh_recent()

    # ── settings ──────────────────────────────────────────────────────────────
    def _open_settings(self):
        def saved():
            self._save_cfg()
            self._v_saxon.set(self.config.get("active_saxon",""))
            # Refresh AI client and re-ping
            self._ai.config = self.config
            self._editor.refresh_ai_status()
            self._editor._ai_panel._update_model_label()
        SettingsDialog(self.root,self.config,saved)

    # ── file menu ─────────────────────────────────────────────────────────────
    def _new(self):
        self._v_xslt.set(""); self._v_xml.set("")
        self._v_extra.set(""); self._current_file=None

    def _open(self):
        p=filedialog.askopenfilename(title="Apri configurazione",
                                     filetypes=[("Saxon config","*.saxcfg"),
                                                ("JSON","*.json"),("All","*.*")])
        if not p: return
        try:
            with open(p,"r",encoding="utf-8") as f: d=json.load(f)
            self._v_xslt.set(d.get("xslt","")); self._v_xml.set(d.get("xml",""))
            self._v_outdir.set(d.get("outdir","")); self._v_outfile.set(d.get("outfile","output.log"))
            self._v_confile.set(d.get("confile","console.log")); self._v_extra.set(d.get("extra",""))
            saxon=d.get("saxon","")
            if saxon:
                if saxon not in self.config.setdefault("saxon_paths",[]): self.config["saxon_paths"].append(saxon)
                self.config["active_saxon"]=saxon; self._v_saxon.set(saxon)
            self._current_file=p
        except Exception as ex: messagebox.showerror("Errore apertura",str(ex))

    def _save(self):
        if self._current_file: self._write_cfg(self._current_file)
        else: self._save_as()

    def _save_as(self):
        p=filedialog.asksaveasfilename(title="Salva configurazione",
                                       defaultextension=".saxcfg",
                                       filetypes=[("Saxon config","*.saxcfg"),
                                                  ("JSON","*.json"),("All","*.*")])
        if p: self._write_cfg(p); self._current_file=p

    def _write_cfg(self,path):
        d=dict(xslt=self._v_xslt.get(),xml=self._v_xml.get(),
               outdir=self._v_outdir.get(),outfile=self._v_outfile.get(),
               confile=self._v_confile.get(),extra=self._v_extra.get(),
               saxon=self.config.get("active_saxon",""))
        try:
            with open(path,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)
            self._set_status(f"💾 Salvato → {path}",C["success"])
        except Exception as ex: messagebox.showerror("Errore salvataggio",str(ex))

    def _about(self):
        messagebox.showinfo("Informazioni",(
            "Saxon XSLT Runner  v3.0\n\n"
            "● Editor XSLT con syntax highlighting\n"
            "● File Watcher: riesecuzione automatica\n"
            "● Debug avanzato: errori cliccabili\n"
            "● AI Locale: autocomplete, check, chat\n"
            "  (Ollama / LM Studio / qualsiasi endpoint OpenAI-compatibile)\n\n"
            f"Config: {CONFIG_FILE}\n\n"
            "Per installare Ollama: https://ollama.com\n"
            "Modelli consigliati: ollama pull mistral\n"
            "                     ollama pull qwen2.5-coder"))

    def _on_close(self):
        if self._editor._dirty:
            ans=messagebox.askyesnocancel("Uscire?",
                "L'editor ha modifiche non salvate. Salvarle prima di uscire?")
            if ans is None: return
            if ans: self._editor.save_file()
        self._watcher.stop(); self.root.destroy()


# ============================================================================
def main():
    root=tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    SaxonRunner(root)
    root.mainloop()

if __name__=="__main__":
    main()
