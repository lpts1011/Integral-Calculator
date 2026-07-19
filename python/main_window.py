import tkinter as tk
from tkinter import ttk

from i18n import LANGUAGE_UI
from math_templates import template_names
from plot_utils import init_plot_area
from progress_utils import ProgressController


def build_main_window(app):
    root = app.root
    root.title("Integral Calculator")
    root.minsize(1100, 700)

    toolbar = ttk.Frame(root)
    toolbar.pack(fill=tk.X, padx=10, pady=(8, 6))
    app.toolbar_row1 = ttk.Frame(toolbar)
    app.toolbar_row2 = ttk.Frame(toolbar)
    app.toolbar_row1.pack(fill=tk.X, pady=(0, 4))
    app.toolbar_row2.pack(fill=tk.X)

    workspace_paned = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
    workspace_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    app.workspace_paned = workspace_paned

    app.left_panel = ttk.Frame(workspace_paned, width=460)
    app.plot_panel = ttk.Frame(workspace_paned, width=1050)
    workspace_paned.add(app.left_panel, weight=1)
    workspace_paned.add(app.plot_panel, weight=4)
    root.after_idle(lambda: _set_initial_sash(workspace_paned, 460))

    app.lang_var = tk.StringVar(value="English")
    app.lang_button = ttk.Combobox(
        app.toolbar_row1,
        textvariable=app.lang_var,
        values=list(LANGUAGE_UI),
        state="readonly",
        width=12,
    )
    app.lang_button.pack(side=tk.LEFT)

    app.usage_button = ttk.Button(app.toolbar_row1, text="Usage Instructions")
    app.usage_button.pack(side=tk.LEFT, padx=8)

    app.template_label = ttk.Label(app.toolbar_row2, text="Template:")
    app.template_label.pack(side=tk.LEFT, padx=(0, 4))
    app.template_var = tk.StringVar(value=template_names()[0])
    app.template_dropdown = ttk.Combobox(
        app.toolbar_row2,
        textvariable=app.template_var,
        values=template_names(),
        state="readonly",
        width=18,
    )
    app.template_dropdown.pack(side=tk.LEFT)
    app.insert_template_button = ttk.Button(app.toolbar_row2, text="Insert Template")
    app.insert_template_button.pack(side=tk.LEFT, padx=(4, 8))

    app.steps_button = ttk.Button(app.toolbar_row2, text="Show Steps")
    app.steps_button.pack(side=tk.LEFT, padx=(0, 8))

    app.suggest_button = ttk.Button(app.toolbar_row2, text="Suggest Input")
    app.suggest_button.pack(side=tk.LEFT, padx=(0, 8))

    app.math_tools_button = ttk.Button(app.toolbar_row2, text="Math Tools")
    app.math_tools_button.pack(side=tk.LEFT, padx=(0, 8))

    app.theme_label = ttk.Label(app.toolbar_row2, text="Theme:")
    app.theme_label.pack(side=tk.LEFT, padx=(8, 4))
    app.theme_var = tk.StringVar(value=app.theme_name)
    app.theme_dropdown = ttk.Combobox(
        app.toolbar_row2,
        textvariable=app.theme_var,
        values=("Light", "Dark"),
        state="readonly",
        width=8,
    )
    app.theme_dropdown.pack(side=tk.LEFT)

    app.notebook = ttk.Notebook(app.left_panel)
    app.notebook.pack(side=tk.TOP, expand=1, fill=tk.BOTH)

    app.tab1_frame = ttk.Frame(app.notebook)
    app.tab2_frame = ttk.Frame(app.notebook)
    app.tab3_frame = ttk.Frame(app.notebook)
    app.notebook.add(app.tab1_frame, text="Basic Integration")
    app.notebook.add(app.tab2_frame, text="Advanced Integration")
    app.notebook.add(app.tab3_frame, text="Improper Integral (Infinite)")

    progress_container = ttk.Frame(app.left_panel, height=20)
    progress_container.pack(fill=tk.X, pady=6)
    progress_container.pack_propagate(False)
    app.progress = ttk.Progressbar(progress_container, orient=tk.HORIZONTAL, mode="determinate")
    app.progress_controller = ProgressController(root, app.progress)

    app.history_frame = ttk.Frame(app.left_panel, height=150)
    app.history_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=(0, 2))
    app.history_frame.pack_propagate(False)

    app.history_label = tk.Label(app.history_frame, text="History:", font=("Arial", 12, "bold"))
    app.history_label.pack(anchor="w", padx=6, pady=(6, 2))

    history_list_container = ttk.Frame(app.history_frame)
    history_list_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    history_scrollbar = ttk.Scrollbar(history_list_container, orient=tk.VERTICAL)
    app.history_listbox = tk.Listbox(
        history_list_container,
        height=5,
        yscrollcommand=history_scrollbar.set,
    )
    history_scrollbar.config(command=app.history_listbox.yview)

    app.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app.plot_fig, app.plot_ax, app.plot_canvas, app.plot_toolbar = init_plot_area(app.plot_panel)


def _set_initial_sash(paned, position):
    try:
        paned.sashpos(0, position)
    except tk.TclError:
        pass
