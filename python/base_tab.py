class BaseTab:
    """Shared small helpers for calculator tab widgets."""

    function_entry_name = "func_entry"

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.worker_running = False
        self.start_time = None

    def clear_entries(self, *entries):
        for entry in entries:
            entry.delete(0, "end")

    def set_entry_text(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def get_function_text(self):
        return getattr(self, self.function_entry_name).get()

    def set_function_text(self, value):
        self.set_entry_text(getattr(self, self.function_entry_name), value)
        self.refresh_after_function_set()

    def set_parameter_text(self, value):
        params_entry = getattr(self, "params_entry", None)
        if params_entry is None:
            return False
        self.set_entry_text(params_entry, value)
        self.refresh_after_function_set()
        return True

    def refresh_after_function_set(self):
        pass

    def clear_result(self):
        self.result_label.config(text="")

    def format_elapsed(self, elapsed):
        if elapsed is None:
            return ""
        label = getattr(self.app, "text", {}).get("time", "Time")
        return f"\n{label}: {elapsed:.3f}s"
