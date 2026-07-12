import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")

from favorites_store import load_favorites, save_favorites
from history_utils import add_history_record
from i18n import ui_text
from language_ui import refresh_usage_window, show_usage_window
from main_window import build_main_window
from math_templates import template_value
from plot_utils import clear_plot, plot_embedded
from tab1_basic import BasicIntegrationTab
from tab2_advanced import AdvancedIntegrationTab
from tab3_improper import ImproperIntegralTab
from theme_utils import THEMES, apply_plot_theme, apply_tk_theme


class IntegralCalculatorApp:
    def __init__(self, root=None):
        self.root = root or tk.Tk()
        self.history = []
        self.usage_window = None
        self.last_raw_result = None
        self.last_raw_result_type = None
        self.last_numeric_value = None
        self.last_record = None
        self.favorites = load_favorites()
        self.theme_name = "Light"
        self.theme = THEMES[self.theme_name]
        self.style = ttk.Style(self.root)
        self.text = ui_text("English")

        build_main_window(self)
        self.tab1 = BasicIntegrationTab(self, self.tab1_frame)
        self.tab2 = AdvancedIntegrationTab(self, self.tab2_frame)
        self.tab3 = ImproperIntegralTab(self, self.tab3_frame)

        self.usage_button.config(command=self.show_usage_instructions)
        self.insert_favorite_button.config(command=self.insert_favorite)
        self.add_favorite_button.config(command=self.add_current_favorite)
        self.insert_template_button.config(command=self.insert_template)
        self.export_button.config(command=self.export_last_result)
        self.steps_button.config(command=self.show_steps)
        self.suggest_button.config(command=self.show_input_suggestions)
        self.math_tools_button.config(command=self.show_math_tools)
        self.lang_button.bind("<<ComboboxSelected>>", lambda event: self.change_language(self.lang_var.get()))
        self.favorite_dropdown.bind("<Return>", lambda event: self.insert_favorite())
        self.theme_dropdown.bind("<<ComboboxSelected>>", lambda event: self.apply_theme(self.theme_var.get()))
        self.history_listbox.bind("<<ListboxSelect>>", self.refill_from_history)
        self.history_listbox.bind("<Double-Button-1>", self.refill_and_compute_from_history)

        self.change_language(self.lang_var.get())
        self.apply_theme(self.theme_name)

    def add_history(self, record):
        add_history_record(self.history, self.history_listbox, record)
        self.last_record = record

    def show_usage_instructions(self):
        self.usage_window = show_usage_window(
            self.root,
            self.usage_window,
            self.lang_var.get(),
        )

    def change_language(self, lang):
        text = ui_text(lang)
        self.text = text
        self.root.title(text["title"])
        for tab_index, tab_text in enumerate(text["tabs"]):
            self.notebook.tab(tab_index, text=tab_text)

        self.usage_button.config(text=text["usage"])
        self.favorite_label.config(text=text["favorite"])
        self.template_label.config(text=text["template"])
        self.insert_favorite_button.config(text=text["insert_favorite"])
        self.insert_template_button.config(text=text["insert_template"])
        self.add_favorite_button.config(text=text["add_favorite"])
        self.export_button.config(text=text["export_last"])
        self.steps_button.config(text=text.get("show_steps", "Show Steps"))
        self.suggest_button.config(text=text.get("suggest_input", "Suggest Input"))
        self.math_tools_button.config(text=text.get("math_tools", "Math Tools"))
        self.theme_label.config(text=text["theme"])
        self.history_label.config(text=text["history"])
        self.tab1.set_language(text)
        self.tab2.set_language(text)
        self.tab3.set_language(text)
        refresh_usage_window(self.usage_window, lang)
        self.apply_theme(self.theme_name)

    def reset_inputs(self):
        for tab in (self.tab1, self.tab2, self.tab3):
            tab.clear_inputs()
            tab.clear_result()

        self.history.clear()
        self.history_listbox.delete(0, tk.END)

        self.progress.stop()
        self.progress.pack_forget()
        self.progress["value"] = 0
        self.clear_plot()

        self.last_raw_result = None
        self.last_raw_result_type = None
        self.last_numeric_value = None
        self.last_record = None
        self.tab1.clear_latex_preview()

    def refill_from_history(self, event):
        selection = self.history_listbox.curselection()
        if not selection:
            return

        record = self.history[selection[0]]
        record_type = record.get("type")
        if record_type in ("definite", "indefinite"):
            self.tab1.refill(record)
            self.notebook.select(self.tab1_frame)
        elif record_type in ("numerical", "symbolic", "symbolic_indefinite", "comparison"):
            self.tab2.refill(record)
            self.notebook.select(self.tab2_frame)
        elif record_type == "improper":
            self.tab3.refill(record)
            self.notebook.select(self.tab3_frame)

    def refill_and_compute_from_history(self, event):
        selection = self.history_listbox.curselection()
        if not selection:
            return

        record = self.history[selection[0]]
        record_type = record.get("type")
        self.refill_from_history(event)

        if record_type in ("definite", "indefinite"):
            self.tab1.calculate()
        elif record_type in ("numerical", "symbolic", "symbolic_indefinite"):
            self.tab2.calculate()
        elif record_type == "improper":
            self.tab3.compute()

    def plot_function(self, func_str, lower, upper, split_points=None):
        plot_embedded(
            func_str,
            lower,
            upper,
            self.plot_ax,
            self.plot_canvas,
            self.theme,
            split_points=split_points,
        )

    def clear_plot(self):
        clear_plot(self.plot_ax, self.plot_canvas, self.theme)

    def insert_favorite(self):
        favorite = self.favorite_var.get().strip()
        if not favorite:
            return
        self.active_tab().set_function_text(favorite)

    def add_current_favorite(self):
        function_text = self.active_tab().get_function_text().strip()
        if not function_text:
            messagebox.showinfo(self.text["favorite_title"], self.text["favorite_empty"])
            return
        if function_text not in self.favorites:
            self.favorites.insert(0, function_text)
            self.favorites = self.favorites[:50]
            save_favorites(self.favorites)
            self.favorite_dropdown.config(values=self.favorites)
        self.favorite_var.set(function_text)
        messagebox.showinfo(self.text["favorite_title"], self.text["favorite_saved"])

    def insert_template(self):
        self.active_tab().set_function_text(template_value(self.template_var.get()))

    def export_last_result(self):
        if not self.last_record:
            messagebox.showinfo(self.text["export_title"], self.text["export_empty"])
            return

        from export_utils import build_latex_export, build_markdown_export

        markdown = build_markdown_export(self.last_record)
        latex = build_latex_export(self.last_record)
        window = tk.Toplevel(self.root)
        window.title(self.text["export_title"])
        text = tk.Text(window, width=90, height=24)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        content = f"Markdown\n\n{markdown}\n\nLaTeX\n\n{latex}"
        text.insert("1.0", content)
        text.focus_set()
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    def show_steps(self):
        from step_explainer import build_steps_for_record

        content = build_steps_for_record(self.last_record)
        window = tk.Toplevel(self.root)
        window.title(self.text.get("show_steps", "Show Steps"))
        text = tk.Text(window, width=90, height=26, wrap="word")
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", content)
        text.config(state="disabled")
        ttk.Button(
            window,
            text=self.text.get("copy", "Copy"),
            command=lambda: self._copy_text(content),
        ).pack(pady=(0, 10))
        self.apply_theme(self.theme_name)

    def show_input_suggestions(self):
        from input_suggestions import suggest_expression, suggestion_report

        current = self.active_tab().get_function_text().strip()
        suggestions = suggest_expression(current)
        window = tk.Toplevel(self.root)
        window.title(self.text.get("suggest_input", "Suggest Input"))
        tk.Label(window, text=suggestion_report(current), justify="left", padx=10, pady=8).pack(anchor="w")
        listbox = tk.Listbox(window, height=max(3, min(6, len(suggestions) or 3)), width=60)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        for suggestion in suggestions:
            listbox.insert(tk.END, suggestion)
        if suggestions:
            listbox.selection_set(0)

        def apply_selected():
            selection = listbox.curselection()
            if not selection:
                return
            self.active_tab().set_function_text(listbox.get(selection[0]))
            window.destroy()

        ttk.Button(
            window,
            text=self.text.get("use_selected", "Use Selected"),
            command=apply_selected,
        ).pack(pady=(0, 10))
        self.apply_theme(self.theme_name)

    def show_math_tools(self):
        from math_tools_ui import show_math_tools_window

        return show_math_tools_window(self)

    def _copy_text(self, content):
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    def active_tab(self):
        selected = self.notebook.select()
        if selected == str(self.tab1_frame):
            return self.tab1
        if selected == str(self.tab2_frame):
            return self.tab2
        return self.tab3

    def apply_theme(self, theme_name):
        self.theme_name = theme_name if theme_name in THEMES else "Light"
        self.theme_var.set(self.theme_name)
        self.theme = apply_tk_theme(self.root, self.style, self.theme_name)
        apply_plot_theme(self.plot_fig, self.plot_ax, self.theme)
        self.plot_canvas.draw_idle()
        for tab in (self.tab1, self.tab2, self.tab3):
            apply_tab_theme = getattr(tab, "apply_theme", None)
            if apply_tab_theme:
                apply_tab_theme(self.theme)

    def run(self):
        self.root.mainloop()


def main():
    IntegralCalculatorApp().run()
