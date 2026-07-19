THEMES = {
    "Light": {
        "bg": "#f6f7f9",
        "panel": "#ffffff",
        "fg": "#1f2933",
        "muted": "#52616b",
        "entry_bg": "#ffffff",
        "entry_fg": "#111827",
        "button_bg": "#e5e7eb",
        "button_fg": "#111827",
        "accent": "#2563eb",
        "accent_fg": "#ffffff",
        "danger": "#ef4444",
        "success": "#15803d",
        "plot_bg": "#ffffff",
        "grid": "#d1d5db",
    },
    "Dark": {
        "bg": "#14171a",
        "panel": "#1f2429",
        "fg": "#e5e7eb",
        "muted": "#a8b3bd",
        "entry_bg": "#111827",
        "entry_fg": "#f9fafb",
        "button_bg": "#374151",
        "button_fg": "#f9fafb",
        "accent": "#3b82f6",
        "accent_fg": "#ffffff",
        "danger": "#b91c1c",
        "success": "#86efac",
        "plot_bg": "#111827",
        "grid": "#374151",
    },
}


def _tk_modules():
    import tkinter as tk
    from tkinter import ttk

    return tk, ttk


def apply_tk_theme(root, style, theme_name):
    tk, _ttk = _tk_modules()
    theme = THEMES.get(theme_name, THEMES["Light"])
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=theme["bg"], foreground=theme["fg"])
    style.configure("TFrame", background=theme["bg"])
    style.configure("TPanedwindow", background=theme["bg"])
    style.configure("TNotebook", background=theme["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=theme["panel"], foreground=theme["fg"], padding=(10, 4))
    style.map("TNotebook.Tab", background=[("selected", theme["entry_bg"])])
    style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
    style.configure(
        "TButton",
        background=theme["button_bg"],
        foreground=theme["button_fg"],
        padding=(8, 4),
    )
    style.map(
        "TButton",
        background=[
            ("pressed", theme["entry_bg"]),
            ("active", theme["panel"]),
            ("!disabled", theme["button_bg"]),
        ],
        foreground=[
            ("disabled", theme["muted"]),
            ("pressed", theme["button_fg"]),
            ("active", theme["button_fg"]),
            ("!disabled", theme["button_fg"]),
        ],
    )
    style.configure("TCombobox", fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"])
    style.configure("Horizontal.TProgressbar", background=theme["accent"], troughcolor=theme["panel"])

    _apply_widget_theme(root, theme)
    return theme


def _apply_widget_theme(widget, theme):
    tk, ttk = _tk_modules()
    if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame)):
        _try_config(widget, bg=theme["bg"])
    elif isinstance(widget, tk.Label):
        fg = theme["success"] if str(widget.cget("fg")) == "green" else theme["fg"]
        _try_config(widget, bg=theme["bg"], fg=fg)
    elif isinstance(widget, tk.Button):
        bg, fg = button_palette(theme, str(widget.cget("text")))
        _try_config(
            widget,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            highlightbackground=bg,
        )
    elif isinstance(widget, tk.Entry):
        _try_config(
            widget,
            bg=theme["entry_bg"],
            fg=theme["entry_fg"],
            insertbackground=theme["entry_fg"],
        )
    elif isinstance(widget, tk.Listbox):
        _try_config(
            widget,
            bg=theme["entry_bg"],
            fg=theme["entry_fg"],
            selectbackground=theme["accent"],
            selectforeground=theme["accent_fg"],
        )
    elif isinstance(widget, tk.Text):
        _try_config(
            widget,
            bg=theme["entry_bg"],
            fg=theme["entry_fg"],
            insertbackground=theme["entry_fg"],
        )

    for child in widget.winfo_children():
        if isinstance(child, ttk.Widget):
            for grandchild in child.winfo_children():
                _apply_widget_theme(grandchild, theme)
        else:
            _apply_widget_theme(child, theme)


def apply_plot_theme(fig, ax, theme):
    fig.patch.set_facecolor(theme["plot_bg"])
    ax.set_facecolor(theme["plot_bg"])
    ax.title.set_color(theme["fg"])
    ax.xaxis.label.set_color(theme["fg"])
    ax.yaxis.label.set_color(theme["fg"])
    ax.tick_params(colors=theme["fg"])
    for spine in ax.spines.values():
        spine.set_color(theme["muted"])


def button_palette(theme, text):
    text = text.lower()
    bg = theme["button_bg"]
    if "calculate" in text or "compute" in text or "insert" in text:
        bg = theme["accent"]
    elif "reset" in text:
        bg = theme["danger"]

    # macOS can ignore tk.Button background colors while still applying fg.
    # Keep the foreground readable on native light buttons even when bg is ignored.
    return bg, theme["button_fg"]


def _try_config(widget, **kwargs):
    tk, _ttk = _tk_modules()
    try:
        widget.config(**kwargs)
    except tk.TclError:
        pass
