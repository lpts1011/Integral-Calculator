import time


class ProgressController:
    def __init__(self, root, progress):
        self.root = root
        self.progress = progress
        self.start_time = None
        self.generation = 0

    def _next_generation(self):
        self.generation += 1
        return self.generation

    def show_indeterminate(self):
        self._next_generation()
        self.start_time = time.time()
        self.progress.stop()
        self.progress.config(mode="indeterminate")
        self.progress.pack(fill="x")
        self.progress.start(10)

    def show_determinate(self, maximum=100):
        self._next_generation()
        self.start_time = None
        self.progress.stop()
        self.progress.config(mode="determinate", maximum=maximum)
        self.progress["value"] = 0
        self.progress.pack(fill="x")

    def hide(self, min_visible=0.3):
        generation = self.generation
        if self.start_time is None:
            self.progress.stop()
            self.progress.pack_forget()
            return

        elapsed = time.time() - self.start_time
        if elapsed >= min_visible:
            self.progress.stop()
            self.progress.pack_forget()
        else:
            delay_ms = int((min_visible - elapsed) * 1000)
            self.root.after(delay_ms, lambda: self._hide_if_current(generation))

    def _hide_if_current(self, generation):
        if generation != self.generation:
            return
        self.progress.stop()
        self.progress.pack_forget()
