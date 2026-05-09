# ui/widget.py
import customtkinter as ctk
import ctypes
import sys

# --- Theme ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

TEAL        = "#3ec9b6"
TEAL_DARK   = "#2aaa99"
TEAL_LIGHT  = "#e6faf7"
TEAL_BORDER = "#c0ede6"
BG          = "#f2f4f3"
CARD        = "#ffffff"
BORDER      = "#dde8e5"
TEXT        = "#1a1a1a"
MUTED       = "#8aa8a2"
AMBER       = "#f0a500"


def _hwnd(widget):
    """Get the real Windows HWND for a tkinter widget."""
    if sys.platform != "win32":
        return None
    hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
    return hwnd if hwnd else widget.winfo_id()


class Card(ctk.CTkFrame):
    """White rounded card matching the mockup style."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
            **kwargs
        )


class SectionLabel(ctk.CTkLabel):
    """Small uppercase section header."""
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent,
            text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=MUTED,
            **kwargs
        )


class SolarWidget(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        # --- Window behaviour ---
        self.overrideredirect(True)
        self.attributes("-topmost", False)
        self.attributes("-alpha", 0.95)
        self.configure(fg_color=BG)

        # --- Size and position ---
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.widget_w = 300
        self.widget_h = screen_h - 40
        x = screen_w - self.widget_w
        y = 0
        self.geometry(f"{self.widget_w}x{self.widget_h}+{x}+{y}")

        # --- Scrollable main container ---
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEAL,
        )
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # --- Build sections ---
        self._build_header()
        self._build_realtime()
        self._build_daily()
        self._build_forecast()

        # --- Push to bottom of Z-order ---
        self.after(200, self._push_to_bottom)

    def _pad(self, pady=(0, 8)):
        """Standard padding frame between sections."""
        ctk.CTkFrame(self.scroll, fg_color=BG, height=pady[1]).pack(fill="x")

    def _build_header(self):
        """Weather + title bar."""
        # Title
        title = ctk.CTkLabel(
            self.scroll,
            text="SOLAR MONITOR — LEIGHTON BUZZARD",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEAL,
        )
        title.pack(anchor="w", padx=14, pady=(6, 1))

        # Weather card
        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 1))

        row = ctk.CTkFrame(card, fg_color=CARD)
        row.pack(fill="x", padx=10, pady=0)

        # Icon + temp
        ctk.CTkLabel(
            row, text="⛅", font=ctk.CTkFont(size=24),
            text_color=TEXT
        ).pack(side="left")

        temp_frame = ctk.CTkFrame(row, fg_color=CARD)
        temp_frame.pack(side="left", padx=8)
        ctk.CTkLabel(
            temp_frame, text="19°C",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            temp_frame, text="Mainly clear · Wind 12 km/h",
            font=ctk.CTkFont(size=10),
            text_color=MUTED
        ).pack(anchor="w")

        # Updated time
        ctk.CTkLabel(
            row, text="Updated\n10:42",
            font=ctk.CTkFont(size=10),
            text_color=MUTED,
            justify="right"
        ).pack(side="right")

        self._pad()

    def _build_realtime(self):
        """Realtime generation section."""
        SectionLabel(self.scroll, "Realtime").pack(
            anchor="w", padx=14, pady=(0, 4))

        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 4))

        row = ctk.CTkFrame(card, fg_color=CARD)
        row.pack(fill="x", padx=12, pady=10)

        # Current generation
        left = ctk.CTkFrame(row, fg_color=CARD)
        left.pack(side="left")
        ctk.CTkLabel(
            left, text="Current generation",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="w")
        gen_row = ctk.CTkFrame(left, fg_color=CARD)
        gen_row.pack(anchor="w")
        ctk.CTkLabel(
            gen_row, text="2.90",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEAL
        ).pack(side="left")
        ctk.CTkLabel(
            gen_row, text=" kW",
            font=ctk.CTkFont(size=12), text_color=MUTED
        ).pack(side="left", pady=(6, 0))

        # Best hour ever
        right = ctk.CTkFrame(row, fg_color=CARD)
        right.pack(side="right")
        ctk.CTkLabel(
            right, text="Best hour ever",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="e")
        bh_row = ctk.CTkFrame(right, fg_color=CARD)
        bh_row.pack(anchor="e")
        ctk.CTkLabel(
            bh_row, text="2.41",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=AMBER
        ).pack(side="left")
        ctk.CTkLabel(
            bh_row, text=" kWh",
            font=ctk.CTkFont(size=12), text_color=MUTED
        ).pack(side="left", pady=(4, 0))

        self._pad()

    def _build_daily(self):
        """Today / This week toggle section."""
        # Toggle buttons
        tog = ctk.CTkFrame(self.scroll, fg_color=BG)
        tog.pack(fill="x", padx=10, pady=(0, 6))
        tog.columnconfigure(0, weight=1)
        tog.columnconfigure(1, weight=1)

        self.btn_today = ctk.CTkButton(
            tog, text="Today",
            fg_color=TEAL, hover_color=TEAL_DARK,
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6, height=28,
            command=self._show_today
        )
        self.btn_today.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.btn_week = ctk.CTkButton(
            tog, text="This week",
            fg_color=CARD, hover_color=TEAL_LIGHT,
            text_color=MUTED, border_color=BORDER, border_width=1,
            font=ctk.CTkFont(size=11),
            corner_radius=6, height=28,
            command=self._show_week
        )
        self.btn_week.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        # Daily stats card
        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 4))

        stats = [
            ("Generated so far", "10.59 kWh", TEAL),
            ("Load satisfied",   "100%",      TEXT),
            ("Exported",         "3.1 kWh",   TEXT),
            ("Export earnings",  "£0.37",     TEAL),
            ("7-day avg generation", "14.3 kWh", TEXT),
            ("7-day avg export", "5.8 kWh · £0.70", TEXT),
        ]

        for i, (label, value, colour) in enumerate(stats):
            row = ctk.CTkFrame(card, fg_color=CARD)
            row.pack(fill="x", padx=12, pady=(6 if i == 0 else 2, 2))
            ctk.CTkLabel(
                row, text=label,
                font=ctk.CTkFont(size=11), text_color=MUTED
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=colour
            ).pack(side="right")

            if i in (1, 3):
                ctk.CTkFrame(
                    card, fg_color=BORDER, height=1
                ).pack(fill="x", padx=12, pady=2)

        # Chart placeholder
        ctk.CTkLabel(
            card, text="7-day hourly profile",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="w", padx=12, pady=(6, 4))

        chart_frame = ctk.CTkFrame(
            card, fg_color="#f2f4f3",
            corner_radius=6, height=60
        )
        chart_frame.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            chart_frame,
            text="[ chart will render here ]",
            font=ctk.CTkFont(size=10),
            text_color=MUTED
        ).pack(expand=True)

        self._pad()

    def _build_forecast(self):
        """3-day forecast + Tea time section."""
        SectionLabel(self.scroll, "Forecast").pack(
            anchor="w", padx=14, pady=(0, 4))

        forecast_days = [
            ("☀️", "Today",    "Sunny, clear skies", "20"),
            ("⛅", "Tomorrow", "Partly cloudy",       "10"),
            ("🌧️", "Sunday",   "Rainy",               "5"),
        ]

        for emoji, day, condition, kwh in forecast_days:
            card = Card(self.scroll)
            card.pack(fill="x", padx=10, pady=(0, 4))

            row = ctk.CTkFrame(card, fg_color=CARD)
            row.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(
                row, text=emoji,
                font=ctk.CTkFont(size=26)
            ).pack(side="left")

            info = ctk.CTkFrame(row, fg_color=CARD)
            info.pack(side="left", padx=8)
            ctk.CTkLabel(
                info, text=day,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT
            ).pack(anchor="w")
            ctk.CTkLabel(
                info, text=condition,
                font=ctk.CTkFont(size=11),
                text_color=MUTED
            ).pack(anchor="w")

            kwh_frame = ctk.CTkFrame(row, fg_color=CARD)
            kwh_frame.pack(side="right")
            ctk.CTkLabel(
                kwh_frame, text=kwh,
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=TEAL_DARK
            ).pack(side="left")
            ctk.CTkLabel(
                kwh_frame, text=" kWh",
                font=ctk.CTkFont(size=11),
                text_color=MUTED
            ).pack(side="left", pady=(4, 0))

        # Tea time card
        self._pad((0, 4))
        tea = Card(self.scroll)
        tea.pack(fill="x", padx=10, pady=(0, 12))

        header = ctk.CTkFrame(tea, fg_color=CARD)
        header.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            header, text="☕",
            font=ctk.CTkFont(size=20)
        ).pack(side="left")
        title_frame = ctk.CTkFrame(header, fg_color=CARD)
        title_frame.pack(side="left", padx=8)
        ctk.CTkLabel(
            title_frame, text="Tea time",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="Best times to use energy today",
            font=ctk.CTkFont(size=10),
            text_color=MUTED
        ).pack(anchor="w")

        slots = [
            ("☀️", "11:00 – 12:00", 0.95),
            ("🌤️", "13:00 – 14:00", 0.80),
            ("🌤️", "14:00 – 15:00", 0.65),
        ]

        for emoji, time_str, strength in slots:
            slot = ctk.CTkFrame(
                tea, fg_color=TEAL_LIGHT,
                corner_radius=6,
                border_width=1, border_color=TEAL_BORDER
            )
            slot.pack(fill="x", padx=12, pady=(0, 4))

            inner = ctk.CTkFrame(slot, fg_color=TEAL_LIGHT)
            inner.pack(fill="x", padx=8, pady=5)

            ctk.CTkLabel(
                inner, text=emoji,
                font=ctk.CTkFont(size=13)
            ).pack(side="left")
            ctk.CTkLabel(
                inner, text=time_str,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=TEAL_DARK
            ).pack(side="left", padx=6)

            bar_bg = ctk.CTkFrame(
                inner, fg_color=TEAL_BORDER,
                corner_radius=2, height=4
            )
            bar_bg.pack(side="right", fill="x", expand=True)
            bar_fill = ctk.CTkFrame(
                bar_bg, fg_color=TEAL,
                corner_radius=2, height=4
            )
            bar_fill.place(relx=0, rely=0, relwidth=strength, relheight=1)

        ctk.CTkFrame(tea, fg_color=CARD, height=4).pack()

    def _show_today(self):
        self.btn_today.configure(
            fg_color=TEAL, text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_week.configure(
            fg_color=CARD, text_color=MUTED,
            font=ctk.CTkFont(size=11))

    def _show_week(self):
        self.btn_week.configure(
            fg_color=TEAL, text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_today.configure(
            fg_color=CARD, text_color=MUTED,
            font=ctk.CTkFont(size=11))

    def _push_to_bottom(self):
        try:
            import win32gui
            import win32con
            hwnd = _hwnd(self)
            if hwnd:
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_BOTTOM,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE |
                    win32con.SWP_NOSIZE |
                    win32con.SWP_NOACTIVATE
                )
        except Exception:
            pass
        self.after(1000, self._push_to_bottom)


if __name__ == "__main__":
    app = SolarWidget()
    app.mainloop()