import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ---------------- Languages ----------------
LANGUAGES = {
    "Detect language": "auto", "English": "en", "Hindi": "hi", "Telugu": "te",
    "Tamil": "ta", "Kannada": "kn", "Malayalam": "ml", "Marathi": "mr",
    "Bengali": "bn", "Gujarati": "gu", "Punjabi": "pa", "Urdu": "ur",
    "Spanish": "es", "French": "fr", "German": "de", "Italian": "it",
    "Portuguese": "pt", "Russian": "ru", "Japanese": "ja", "Korean": "ko",
    "Chinese (Simplified)": "zh", "Arabic": "ar", "Turkish": "tr",
    "Dutch": "nl", "Indonesian": "id", "Thai": "th",
}
CODE_TO_NAME = {v: k for k, v in LANGUAGES.items()}


# ---------------- Translation API functions ----------------
def google_translate(text, source, target, api_key):
    """Google Cloud Translation API v2."""
    url = "https://translation.googleapis.com/language/translate/v2"
    payload = {"q": text, "target": target, "format": "text", "key": api_key}
    if source != "auto":
        payload["source"] = source
    response = requests.post(url, data=payload, timeout=15)
    data = response.json()
    if response.status_code != 200:
        raise Exception(data.get("error", {}).get("message", "Google API error"))
    result = data["data"]["translations"][0]
    return result["translatedText"], result.get("detectedSourceLanguage")


def mymemory_translate(text, source, target):
    """Free API for demos. No key needed."""
    if source == "auto":
        raise Exception("MyMemory needs a specific source language.")
    url = "https://api.mymemory.translated.net/get"
    response = requests.get(
        url, params={"q": text, "langpair": f"{source}|{target}"}, timeout=15
    )
    data = response.json()
    if data.get("responseStatus") != 200:
        raise Exception(data.get("responseDetails", "MyMemory error"))
    return data["responseData"]["translatedText"], None


# ---------------- GUI ----------------
class TranslatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Language Translation Tool")
        self.geometry("900x600")
        self.minsize(750, 520)
        self.configure(padx=15, pady=15)
        self.build_ui()

    def build_ui(self):
        tk.Label(self, text="🌐 Language Translation Tool",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")

        # --- Service + API key ---
        top = tk.Frame(self)
        top.pack(fill="x", pady=(10, 5))

        tk.Label(top, text="Service:").grid(row=0, column=0, sticky="w")
        self.provider = ttk.Combobox(
            top, state="readonly", width=28,
            values=["Google Cloud Translation", "MyMemory (free)"])
        self.provider.current(1)  # default to free option for easy testing
        self.provider.grid(row=0, column=1, padx=8)
        self.provider.bind("<<ComboboxSelected>>", self.toggle_key)

        self.key_label = tk.Label(top, text="API key:")
        self.key_entry = tk.Entry(top, show="*", width=40)
        self.key_label.grid(row=0, column=2, padx=(15, 5))
        self.key_entry.grid(row=0, column=3)
        self.toggle_key()

        # --- Language selectors ---
        langs = tk.Frame(self)
        langs.pack(fill="x", pady=10)

        tk.Label(langs, text="From:").pack(side="left")
        self.src = ttk.Combobox(langs, state="readonly", width=22,
                                values=list(LANGUAGES.keys()))
        self.src.set("English")
        self.src.pack(side="left", padx=8)

        tk.Button(langs, text="⇄ Swap", command=self.swap).pack(side="left", padx=8)

        tk.Label(langs, text="To:").pack(side="left", padx=(10, 0))
        self.tgt = ttk.Combobox(
            langs, state="readonly", width=22,
            values=[n for n in LANGUAGES if n != "Detect language"])
        self.tgt.set("Hindi")
        self.tgt.pack(side="left", padx=8)

        # --- Text areas ---
        panels = tk.Frame(self)
        panels.pack(fill="both", expand=True)
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(1, weight=1)

        tk.Label(panels, text="Enter text").grid(row=0, column=0, sticky="w")
        tk.Label(panels, text="Translation").grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.input_box = tk.Text(panels, wrap="word", font=("Segoe UI", 12), height=10)
        self.input_box.grid(row=1, column=0, sticky="nsew")

        self.output_box = tk.Text(panels, wrap="word", font=("Segoe UI", 12),
                                  height=10, bg="#f4f7ff", state="disabled")
        self.output_box.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        # --- Buttons under each box ---
        left_btns = tk.Frame(panels)
        left_btns.grid(row=2, column=0, sticky="w", pady=6)
        tk.Button(left_btns, text="🔊 Listen",
                  command=lambda: self.speak(self.input_box.get("1.0", "end").strip())
                  ).pack(side="left")
        tk.Button(left_btns, text="Clear", command=self.clear).pack(side="left", padx=6)

        right_btns = tk.Frame(panels)
        right_btns.grid(row=2, column=1, sticky="w", pady=6, padx=(10, 0))
        tk.Button(right_btns, text="📋 Copy", command=self.copy_output).pack(side="left")
        tk.Button(right_btns, text="🔊 Listen",
                  command=lambda: self.speak(self.get_output())).pack(side="left", padx=6)

        # --- Translate button + status ---
        self.translate_btn = tk.Button(
            self, text="Translate", font=("Segoe UI", 12, "bold"),
            bg="#3b6cf6", fg="white", padx=20, pady=6, command=self.start_translate)
        self.translate_btn.pack(anchor="w", pady=(5, 0))

        self.status = tk.Label(self, text="", fg="gray")
        self.status.pack(anchor="w", pady=5)

    # ---------- Helpers ----------
    def toggle_key(self, event=None):
        if self.provider.get().startswith("Google"):
            self.key_label.grid()
            self.key_entry.grid()
        else:
            self.key_label.grid_remove()
            self.key_entry.grid_remove()

    def set_status(self, msg, error=False):
        self.status.config(text=msg, fg="red" if error else "gray")

    def get_output(self):
        return self.output_box.get("1.0", "end").strip()

    def set_output(self, text):
        self.output_box.config(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", text)
        self.output_box.config(state="disabled")

    def swap(self):
        if self.src.get() == "Detect language":
            self.set_status("Choose a specific source language to swap.", True)
            return
        s, t = self.src.get(), self.tgt.get()
        self.src.set(t)
        self.tgt.set(s)
        out = self.get_output()
        if out:
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", out)
            self.set_output("")

    def clear(self):
        self.input_box.delete("1.0", "end")
        self.set_output("")
        self.set_status("")

    def copy_output(self):
        text = self.get_output()
        if not text:
            self.set_status("Nothing to copy.", True)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("Copied to clipboard ✓")

    # ---------- Text to speech ----------
    def speak(self, text):
        if not text:
            return
        if not TTS_AVAILABLE:
            messagebox.showinfo("Text-to-speech",
                                "Install it with:  pip install pyttsx3")
            return

        def run():
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()

        threading.Thread(target=run, daemon=True).start()

    # ---------- Translation ----------
    def start_translate(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            self.set_status("Please enter some text.", True)
            return
        source = LANGUAGES[self.src.get()]
        target = LANGUAGES[self.tgt.get()]
        if source == target:
            self.set_status("Source and target languages are the same.", True)
            return

        use_google = self.provider.get().startswith("Google")
        api_key = self.key_entry.get().strip()
        if use_google and not api_key:
            self.set_status("Enter your Google API key first.", True)
            return

        self.translate_btn.config(state="disabled")
        self.set_status("Translating...")

        # Run in a background thread so the window doesn't freeze
        threading.Thread(
            target=self.do_translate,
            args=(text, source, target, use_google, api_key),
            daemon=True).start()

    def do_translate(self, text, source, target, use_google, api_key):
        try:
            if use_google:
                result, detected = google_translate(text, source, target, api_key)
            else:
                result, detected = mymemory_translate(text, source, target)
            self.after(0, self.on_success, result, detected)
        except Exception as e:
            self.after(0, self.on_error, str(e))

    def on_success(self, result, detected):
        self.set_output(result)
        if detected:
            self.set_status(f"Detected source: {CODE_TO_NAME.get(detected, detected)}")
        else:
            self.set_status("Done ✓")
        self.translate_btn.config(state="normal")

    def on_error(self, message):
        self.set_status(message, True)
        self.translate_btn.config(state="normal")


if __name__ == "__main__":
    TranslatorApp().mainloop()