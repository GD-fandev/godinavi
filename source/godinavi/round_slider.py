import tkinter as tk


class RoundSlider(tk.Canvas):
    """Compact horizontal slider with a conventional circular thumb."""

    def __init__(self, master, value=0, length=90, minimum=0, maximum=100,
                 background="#17130f", trough="#2a2118", fill="#d8b15a",
                 thumb="#f6dfaa", outline="#6f5c3e"):
        self.minimum = int(minimum)
        self.maximum = max(self.minimum + 1, int(maximum))
        self.value = self.minimum
        self.length = int(length)
        self.thumb_radius = 6
        super().__init__(master, width=self.length, height=18, bg=background,
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self.trough_color = trough
        self.fill_color = fill
        self.thumb_color = thumb
        self.outline_color = outline
        self.bind("<Button-1>", self._set_from_pointer, add="+")
        self.bind("<B1-Motion>", self._set_from_pointer, add="+")
        self.bind("<Left>", lambda _event: self.set(self.value - 1), add="+")
        self.bind("<Right>", lambda _event: self.set(self.value + 1), add="+")
        self.bind("<Configure>", lambda _event: self._draw(), add="+")
        self.set(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = max(self.minimum, min(self.maximum, round(float(value))))
        self._draw()

    def _set_from_pointer(self, event):
        self.focus_set()
        left = self.thumb_radius + 1
        right = max(left + 1, self.winfo_width() - self.thumb_radius - 1)
        ratio = max(0.0, min(1.0, (event.x - left) / (right - left)))
        self.set(self.minimum + ratio * (self.maximum - self.minimum))

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("slider")
        center = max(1, self.winfo_height() // 2)
        left = self.thumb_radius + 1
        right = max(left + 1, self.winfo_width() - self.thumb_radius - 1)
        ratio = (self.value - self.minimum) / (self.maximum - self.minimum)
        thumb_x = round(left + (right - left) * ratio)
        self.create_line(left, center, right, center, fill=self.trough_color, width=4, capstyle="round", tags="slider")
        self.create_line(left, center, thumb_x, center, fill=self.fill_color, width=4, capstyle="round", tags="slider")
        radius = self.thumb_radius
        self.create_oval(thumb_x - radius, center - radius, thumb_x + radius, center + radius,
                         fill=self.thumb_color, outline=self.outline_color, width=1, tags="slider")
