import tkinter as tk

from i18n import INSTRUCTIONS, LANGUAGE_UI


def refresh_usage_window(usage_window, lang):
    if usage_window is None or not usage_window.winfo_exists():
        return
    usage_text = "\n".join(INSTRUCTIONS.get(lang, INSTRUCTIONS["English"]))
    for widget in usage_window.winfo_children():
        widget.destroy()
    usage_label = tk.Label(usage_window, text=usage_text, justify="left", padx=10, pady=10)
    usage_label.pack()


def show_usage_window(root, usage_window, lang):
    if usage_window is not None and not usage_window.winfo_exists():
        usage_window = None
    if usage_window is not None:
        try:
            usage_window.lift()
            refresh_usage_window(usage_window, lang)
            return usage_window
        except tk.TclError:
            usage_window = None

    usage_window = tk.Toplevel(root)
    usage_window.title(LANGUAGE_UI.get(lang, LANGUAGE_UI["English"])["usage"])
    refresh_usage_window(usage_window, lang)

    def on_usage_close():
        if usage_window is not None and usage_window.winfo_exists():
            usage_window.destroy()

    usage_window.protocol("WM_DELETE_WINDOW", on_usage_close)
    return usage_window
