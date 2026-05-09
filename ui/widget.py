# ui/widget.py
import customtkinter as ctk
import ctypes
import win32gui
import win32con

def set_always_on_bottom(hwnd):
    """Push window to the bottom of the Z-order (behind all other windows)."""
    win32gui.SetWindowPos(
        hwnd,
        win32con.HWND_BOTTOM,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    )

class SolarWidget(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window behaviour ---
        self.overrideredirect(True)       # no title bar or borders
        self.attributes("-topmost", False)
        self.attributes("-alpha", 0.95)   # slight transparency

        # --- Size and position ---
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        widget_w = 300
        widget_h = screen_h - 40          # leave room for taskbar
        x = screen_w - widget_w
        y = 0


        self.geometry(f"{widget_w}x{widget_h}+{x}+{y}")
        self.configure(fg_color="#f2f4f3")

        # --- Placeholder label ---
        label = ctk.CTkLabel(
            self,
            text="Solar Monitor\nLeighton Buzzard",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#3ec9b6"
        )
        label.pack(expand=True)

        # --- Push to bottom after window loads ---
        self.after(100, self._push_to_bottom)

    def _push_to_bottom(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        if hwnd == 0:
            hwnd = self.winfo_id()
        set_always_on_bottom(hwnd)
        self.after(1000, self._push_to_bottom)  # keep pushing every second

if __name__ == "__main__":
    app = SolarWidget()
    app.mainloop()