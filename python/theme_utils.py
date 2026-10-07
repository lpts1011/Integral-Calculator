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


def apply_plot_theme(fig, ax, theme):
    fig.patch.set_facecolor(theme["plot_bg"])
    ax.set_facecolor(theme["plot_bg"])
    ax.title.set_color(theme["fg"])
    ax.xaxis.label.set_color(theme["fg"])
    ax.yaxis.label.set_color(theme["fg"])
    ax.tick_params(colors=theme["fg"])
    for spine in ax.spines.values():
        spine.set_color(theme["muted"])
