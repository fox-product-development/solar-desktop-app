# ui/widget.py
import datetime
import tkinter as tk
import customtkinter as ctk
import ctypes
import sys
import config
from core import data_store
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

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
    if sys.platform != "win32":
        return None
    hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
    return hwnd if hwnd else widget.winfo_id()


class Card(ctk.CTkFrame):
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
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent,
            text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=MUTED,
            **kwargs
        )


class LongTermPanel:
    PANEL_WIDTH = 210
    SLIDE_STEPS = 15
    SLIDE_DELAY = 10

    def __init__(self, main_widget):
        self.main = main_widget
        self.is_open = False
        self._animating = False
        self._current_period = "year"
        self._ref_date = datetime.date.today()

        self.win = tk.Toplevel(main_widget)
        self.win.overrideredirect(True)
        self.win.attributes("-alpha", 0.7)
        self.win.configure(bg=BG)
        self.win.withdraw()

        self._build_content()

    def _get_positions(self):
        main_x     = self.main.winfo_x()
        main_y     = self.main.winfo_y()
        realtime_y = main_y + self.main.realtime_y_offset
        open_x     = main_x - self.PANEL_WIDTH
        closed_x   = main_x
        panel_h    = self.main.realtime_section_height
        return open_x, closed_x, realtime_y, panel_h

    def _build_content(self):
        chip_frame = tk.Frame(self.win, bg=BG)
        chip_frame.pack(fill="x", padx=10, pady=(12, 6))

        self._chip_btns = {}
        for period in ["Week", "Month", "Year", "Lifetime"]:
            btn = ctk.CTkButton(
                chip_frame, text=period,
                width=44, height=24,
                font=ctk.CTkFont(size=10),
                corner_radius=4,
                fg_color=TEAL if period == "Year" else CARD,
                text_color="white" if period == "Year" else MUTED,
                border_color=TEAL if period == "Year" else BORDER,
                border_width=1,
                hover_color=TEAL_LIGHT,
                command=lambda p=period: self._select_period(p)
            )
            btn.pack(side="left", padx=(0, 3))
            self._chip_btns[period] = btn

        nav = ctk.CTkFrame(self.win, fg_color=BG)
        nav.pack(fill="x", padx=10, pady=(0, 8))
        nav.columnconfigure(1, weight=1)

        ctk.CTkButton(
            nav, text="‹", width=24, height=24,
            font=ctk.CTkFont(size=16),
            fg_color=CARD, text_color=MUTED,
            border_color=BORDER, border_width=1,
            corner_radius=5, hover_color=TEAL_LIGHT,
            command=self._prev_period
        ).grid(row=0, column=0)

        self._period_label = ctk.CTkLabel(
            nav, text="2026",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT)
        self._period_label.grid(row=0, column=1)

        ctk.CTkButton(
            nav, text="›", width=24, height=24,
            font=ctk.CTkFont(size=16),
            fg_color=CARD, text_color=MUTED,
            border_color=BORDER, border_width=1,
            corner_radius=5, hover_color=TEAL_LIGHT,
            command=self._next_period
        ).grid(row=0, column=2)

        card = Card(self.win)
        card.pack(fill="x", padx=10, pady=(0, 8))

        self._lt_refs = {}
        stats = [
            ("lt_gen",      "Total generation", "--", TEAL),
            ("lt_export",   "Total export",     "--", TEXT),
            ("lt_earnings", "Export earnings",  "--", TEAL),
        ]

        for i, (key, label, value, colour) in enumerate(stats):
            ctk.CTkLabel(
                card, text=label,
                font=ctk.CTkFont(size=11), text_color=MUTED
            ).pack(anchor="w", padx=12, pady=(8 if i == 0 else 2, 0))
            val_lbl = ctk.CTkLabel(
                card, text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=colour)
            val_lbl.pack(anchor="w", padx=12, pady=(0, 4))
            self._lt_refs[key] = val_lbl

            if i < 2:
                ctk.CTkFrame(
                    card, fg_color=BORDER, height=1
                ).pack(fill="x", padx=12, pady=2)

        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(
            fill="x", padx=12, pady=2)
        ctk.CTkLabel(
            card, text="Payoff progress",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="w", padx=12, pady=(4, 2))

        progress_bg = ctk.CTkFrame(
            card, fg_color="#e8eeec", corner_radius=3, height=6)
        progress_bg.pack(fill="x", padx=12, pady=(0, 4))
        self._lt_refs["roi_bar"] = ctk.CTkFrame(
            progress_bg, fg_color=TEAL, corner_radius=3, height=6)
        self._lt_refs["roi_bar"].place(
            relx=0, rely=0, relwidth=0.01, relheight=1)

        self._lt_refs["roi_label"] = ctk.CTkLabel(
            card, text="Set install cost to track payoff",
            font=ctk.CTkFont(size=10), text_color=MUTED)
        self._lt_refs["roi_label"].pack(
            anchor="w", padx=12, pady=(0, 8))

    def _select_period(self, period):
        self._current_period = period.lower()
        self._ref_date = datetime.date.today()
        for p, btn in self._chip_btns.items():
            if p == period:
                btn.configure(fg_color=TEAL, text_color="white", border_color=TEAL)
            else:
                btn.configure(fg_color=CARD, text_color=MUTED, border_color=BORDER)
        self._refresh_data()

    def _prev_period(self):
        if self._current_period == "year":
            self._ref_date = self._ref_date.replace(year=self._ref_date.year - 1)
        elif self._current_period == "month":
            if self._ref_date.month == 1:
                self._ref_date = self._ref_date.replace(year=self._ref_date.year - 1, month=12)
            else:
                self._ref_date = self._ref_date.replace(month=self._ref_date.month - 1)
        elif self._current_period == "week":
            self._ref_date -= datetime.timedelta(weeks=1)
        self._refresh_data()

    def _next_period(self):
        if self._current_period == "year":
            self._ref_date = self._ref_date.replace(year=self._ref_date.year + 1)
        elif self._current_period == "month":
            if self._ref_date.month == 12:
                self._ref_date = self._ref_date.replace(year=self._ref_date.year + 1, month=1)
            else:
                self._ref_date = self._ref_date.replace(month=self._ref_date.month + 1)
        elif self._current_period == "week":
            self._ref_date += datetime.timedelta(weeks=1)
        self._refresh_data()

    def _refresh_data(self):
        period = self._current_period
        label  = data_store.get_period_label(period, self._ref_date)
        totals = data_store.get_period_totals(period, self._ref_date)

        self._period_label.configure(text=label)
        self._lt_refs["lt_gen"].configure(text=f"{totals['generation_kwh']:.1f} kWh")
        self._lt_refs["lt_export"].configure(text=f"{totals['export_kwh']:.1f} kWh")
        self._lt_refs["lt_earnings"].configure(text=f"£{totals['earnings_gbp']:.2f}")

        store = data_store.get_all()
        payoff = store.get("install_cost_gbp")
        if payoff:
            total_earn = store.get("cumulative_export_earnings_gbp", 0.0)
            pct = min(1.0, total_earn / payoff)
            self._lt_refs["roi_bar"].place(relwidth=pct)
            self._lt_refs["roi_label"].configure(
                text=f"£{total_earn:.2f} of £{payoff:.0f} · {pct*100:.1f}%")

    def update_data(self, store):
        """Called on every UI refresh — updates with current period data."""
        self._refresh_data()

    def toggle(self):
        if self._animating:
            return
        if self.is_open:
            self._slide_close()
        else:
            self._slide_open()

    def _slide_open(self):
        self._animating = True
        self.is_open = True
        open_x, closed_x, realtime_y, panel_h = self._get_positions()
        self.win.geometry(f"{self.PANEL_WIDTH}x{panel_h}+{closed_x}+{realtime_y}")
        self.win.deiconify()
        self._push_to_bottom()
        step = (open_x - closed_x) / self.SLIDE_STEPS
        self._animate(closed_x, open_x, step, realtime_y, panel_h)

    def _slide_close(self):
        self._animating = True
        self.is_open = False
        open_x, closed_x, realtime_y, panel_h = self._get_positions()
        step = (closed_x - open_x) / self.SLIDE_STEPS
        self._animate(open_x, closed_x, step, realtime_y, panel_h)

    def _animate(self, current_x, target_x, step, y, h):
        current_x += step
        done = (step > 0 and current_x >= target_x) or \
               (step < 0 and current_x <= target_x)
        x = target_x if done else int(current_x)
        self.win.geometry(f"{self.PANEL_WIDTH}x{h}+{x}+{y}")
        if done:
            self._animating = False
            if not self.is_open:
                self.win.withdraw()
        else:
            self.win.after(
                self.SLIDE_DELAY,
                lambda: self._animate(current_x, target_x, step, y, h))

    def _push_to_bottom(self):
        try:
            import win32gui
            import win32con
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            if not hwnd:
                hwnd = self.win.winfo_id()
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                win32con.SWP_NOACTIVATE)
        except Exception:
            pass
        if self.is_open:
            self.win.after(1000, self._push_to_bottom)


class SolarWidget(ctk.CTk):

    def __init__(self, refresher=None):
        super().__init__()
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        self.refresher = refresher
        self._refs = {}
        self.realtime_y_offset = 230
        self.realtime_section_height = 280
        self.lt_panel = None
        self._daily_mode = "today"  # "today" or "week"

        self.overrideredirect(True)
        self.attributes("-topmost", False)
        self.attributes("-alpha", 0.7)
        self.configure(fg_color=BG)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.widget_w = 300
        self.widget_h = screen_h - 40
        x = screen_w - self.widget_w
        y = 0
        self.geometry(f"{self.widget_w}x{self.widget_h}+{x}+{y}")

        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=TEAL,
        )
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_header()
        self._build_realtime()
        self._build_daily()
        self._build_forecast()

        self.after(1000, self._update_ui)
        self.after(800, self._init_long_term_panel)
        self.after(200, self._push_to_bottom)

    def _pad(self, height=4):
        ctk.CTkFrame(self.scroll, fg_color=BG, height=height).pack(fill="x")

    def _init_long_term_panel(self):
        self.update_idletasks()
        self.lt_panel = LongTermPanel(self)
        self._build_tab_button()

    def _build_tab_button(self):
        tab_w = 15
        tab_h = 120

        tab_frame = tk.Frame(
            self,
            width=tab_w,
            height=tab_h,
            bg=TEAL,
            cursor="hand2"
        )
        tab_frame.place(x=0, y=self.realtime_y_offset)
        tab_frame.tkraise()

        tab_lbl = tk.Label(
            tab_frame,
            text="L\nO\nN\nG\n\nT\nE\nR\nM",
            bg=TEAL,
            fg="white",
            font=("Segoe UI", 6, "bold"),
            cursor="hand2",
            justify="center"
        )
        tab_lbl.place(relx=0.5, rely=0.5, anchor="center")

        tab_frame.bind("<Button-1>", lambda e: self._toggle_lt_panel())
        tab_lbl.bind("<Button-1>", lambda e: self._toggle_lt_panel())
        self._tab_frame = tab_frame

    def _toggle_lt_panel(self):
        if self.lt_panel:
            self.lt_panel.toggle()

    # ------------------------------------------------------------------ #
    # Layout builders                                                      #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        title = ctk.CTkLabel(
            self.scroll,
            text="SOLAR MONITOR — LEIGHTON BUZZARD",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEAL,
        )
        title.pack(anchor="w", padx=14, pady=(8, 2))

        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 2))

        row = ctk.CTkFrame(card, fg_color=CARD)
        row.pack(fill="x", padx=10, pady=1)

        self._refs["weather_icon"] = ctk.CTkLabel(
            row, text="--", font=ctk.CTkFont(size=24), text_color=TEXT)
        self._refs["weather_icon"].pack(side="left")

        temp_frame = ctk.CTkFrame(row, fg_color=CARD)
        temp_frame.pack(side="left", padx=8)

        self._refs["temp"] = ctk.CTkLabel(
            temp_frame, text="--°C",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT)
        self._refs["temp"].pack(anchor="w")

        self._refs["condition"] = ctk.CTkLabel(
            temp_frame, text="Loading...",
            font=ctk.CTkFont(size=10), text_color=MUTED)
        self._refs["condition"].pack(anchor="w")

        self._refs["updated"] = ctk.CTkLabel(
            row, text="Updated\n--:--",
            font=ctk.CTkFont(size=10), text_color=MUTED, justify="right")
        self._refs["updated"].pack(side="right")

        self._pad()

    def _build_realtime(self):
        SectionLabel(self.scroll, "Realtime").pack(
            anchor="w", padx=14, pady=(0, 4))

        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 4))

        row = ctk.CTkFrame(card, fg_color=CARD)
        row.pack(fill="x", padx=12, pady=10)

        left = ctk.CTkFrame(row, fg_color=CARD)
        left.pack(side="left")
        ctk.CTkLabel(
            left, text="Current generation",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="w")
        gen_row = ctk.CTkFrame(left, fg_color=CARD)
        gen_row.pack(anchor="w")
        self._refs["pv_power"] = ctk.CTkLabel(
            gen_row, text="--",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=TEAL)
        self._refs["pv_power"].pack(side="left")
        ctk.CTkLabel(
            gen_row, text=" kW",
            font=ctk.CTkFont(size=12), text_color=MUTED
        ).pack(side="left", pady=(6, 0))

        right = ctk.CTkFrame(row, fg_color=CARD)
        right.pack(side="right")
        ctk.CTkLabel(
            right, text="Best day ever",
            font=ctk.CTkFont(size=11), text_color=MUTED
        ).pack(anchor="e")
        bd_num_row = ctk.CTkFrame(right, fg_color=CARD)
        bd_num_row.pack(anchor="e")
        self._refs["best_day_kwh"] = ctk.CTkLabel(
            bd_num_row, text="--",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=TEAL)
        self._refs["best_day_kwh"].pack(side="left")
        ctk.CTkLabel(
            bd_num_row, text=" kWh",
            font=ctk.CTkFont(size=12), text_color=MUTED
        ).pack(side="left", pady=(6, 0))
        self._refs["best_day_date"] = ctk.CTkLabel(  # font size=11 — adjust if needed
            right, text="",
            font=ctk.CTkFont(size=11), text_color=MUTED)
        self._refs["best_day_date"].pack(anchor="e")

        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=12)

        self._pad()

    def _build_daily(self):
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

        card = Card(self.scroll)
        card.pack(fill="x", padx=10, pady=(0, 4))

        stat_keys = [
            ("generated",  "Generated so far",      "--",  TEAL),
            ("load_pct",   "Load satisfied",         "--",  TEXT),
            ("exported",   "Exported",               "--",  TEXT),
            ("earnings",   "Export earnings",        "--",  TEAL),
            ("avg_gen",    "7-day avg generation",   "--",  TEXT),
            ("avg_export", "7-day avg export",       "--",  TEXT),
        ]

        for i, (key, label, value, colour) in enumerate(stat_keys):
            row = ctk.CTkFrame(card, fg_color=CARD)
            row.pack(fill="x", padx=12, pady=(4 if i == 0 else 1, 1))
            ctk.CTkLabel(
                row, text=label,
                font=ctk.CTkFont(size=11), text_color=MUTED
            ).pack(side="left")
            ref = ctk.CTkLabel(
                row, text=value,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=colour
            )
            ref.pack(side="right")
            self._refs[key] = ref

            if i in (1, 3):
                ctk.CTkFrame(
                    card, fg_color=BORDER, height=1
                ).pack(fill="x", padx=12, pady=2)

        self._pad()

    def _build_forecast(self):
        SectionLabel(self.scroll, "Forecast").pack(
            anchor="w", padx=14, pady=(0, 4))

        forecast_days = [
            ("--", "Today",    "--", "--"),
            ("--", "Tomorrow", "--", "--"),
            ("--", "Sunday",   "--", "--"),
        ]

        for i, (emoji, day, condition, kwh) in enumerate(forecast_days):
            card = Card(self.scroll)
            card.pack(fill="x", padx=10, pady=(0, 4))

            row = ctk.CTkFrame(card, fg_color=CARD)
            row.pack(fill="x", padx=12, pady=5)

            icon = ctk.CTkLabel(row, text=emoji, font=ctk.CTkFont(size=26))
            icon.pack(side="left")
            self._refs[f"fcast_icon_{i}"] = icon

            info = ctk.CTkFrame(row, fg_color=CARD)
            info.pack(side="left", padx=8)

            day_label = ctk.CTkLabel(
                info, text=day,
                font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT)
            day_label.pack(anchor="w")
            self._refs[f"fcast_day_{i}"] = day_label

            cond_label = ctk.CTkLabel(
                info, text=condition,
                font=ctk.CTkFont(size=11), text_color=MUTED)
            cond_label.pack(anchor="w")
            self._refs[f"fcast_cond_{i}"] = cond_label

            kwh_frame = ctk.CTkFrame(row, fg_color=CARD)
            kwh_frame.pack(side="right")

            kwh_label = ctk.CTkLabel(
                kwh_frame, text=kwh,
                font=ctk.CTkFont(size=18, weight="bold"), text_color=TEAL_DARK)
            kwh_label.pack(side="left")
            self._refs[f"fcast_kwh_{i}"] = kwh_label

            ctk.CTkLabel(
                kwh_frame, text=" kWh",
                font=ctk.CTkFont(size=11), text_color=MUTED
            ).pack(side="left", pady=(4, 0))

        # Tea time card
        self._pad(4)
        tea = Card(self.scroll)
        tea.pack(fill="x", padx=10, pady=(0, 6))

        header = ctk.CTkFrame(tea, fg_color=CARD)
        header.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(header, text="☕", font=ctk.CTkFont(size=20)).pack(side="left")
        title_frame = ctk.CTkFrame(header, fg_color=CARD)
        title_frame.pack(side="left", padx=8)
        ctk.CTkLabel(
            title_frame, text="Tea time",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="Best times for a cuppa",
            font=ctk.CTkFont(size=10), text_color=MUTED
        ).pack(anchor="w")

        self._refs["tea_slots"] = []
        for j in range(3):
            slot = ctk.CTkFrame(
                tea, fg_color=TEAL_LIGHT,
                corner_radius=6, border_width=1, border_color=TEAL_BORDER)
            slot.pack(fill="x", padx=12, pady=(0, 4))

            inner = ctk.CTkFrame(slot, fg_color=TEAL_LIGHT)
            inner.pack(fill="x", padx=8, pady=6)
            inner.columnconfigure(0, minsize=80)
            inner.columnconfigure(1, weight=1)
            inner.columnconfigure(2, minsize=70)

            time_lbl = ctk.CTkLabel(
                inner, text="--",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=TEAL_DARK, anchor="w")
            time_lbl.grid(row=0, column=0, sticky="w")

            bar_bg = ctk.CTkFrame(
                inner, fg_color=TEAL_BORDER, corner_radius=2, height=6)
            bar_bg.grid(row=0, column=1, sticky="ew", padx=(4, 4))
            bar_fill = ctk.CTkFrame(
                bar_bg, fg_color=TEAL, corner_radius=2, height=6)
            bar_fill.place(relx=0, rely=0, relwidth=0.5, relheight=1)

            kwh_lbl = ctk.CTkLabel(
                inner, text="",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=TEAL_DARK, anchor="e")
            kwh_lbl.grid(row=0, column=2, sticky="e")

            self._refs["tea_slots"].append({
                "time": time_lbl,
                "bar":  bar_fill,
                "kwh":  kwh_lbl,
            })

        # Today's generation forecast chart inside tea time card
        chart_frame = ctk.CTkFrame(tea, fg_color=CARD, corner_radius=6)
        chart_frame.pack(fill="x", padx=12, pady=(10, 10))

        fig = Figure(figsize=(2.5, 0.7), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#f2f4f3")

        hours  = list(range(24))
        values = [0]*24

        ax.bar(hours, values, color="#3ec9b6", width=0.8, alpha=0.7)
        ax.set_xlim(-0.5, 23.5)
        ax.set_ylim(0, 3.2)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["00:00", "06:00", "12:00", "18:00", "23:00"],
                           fontsize=7, color="#8aa8a2")
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#dde8e5")
        ax.tick_params(axis="x", length=0)
        fig.tight_layout(pad=0.3)

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x")
        self._refs["chart_ax"] = ax
        self._refs["chart_canvas"] = canvas

    # ------------------------------------------------------------------ #
    # Live data update                                                     #
    # ------------------------------------------------------------------ #

    def _update_ui(self):
        if self.refresher:
            snap    = self.refresher.snapshot()
            live    = snap.get("live")
            weather = snap.get("weather")
            store   = snap.get("store", {})

            if weather and not weather.get("error"):
                self._refs["weather_icon"].configure(text=weather["emoji"])
                self._refs["temp"].configure(text=f"{weather['temperature']}°C")
                self._refs["condition"].configure(
                    text=f"{weather['description']} · Wind {weather['wind_kph']} km/h")
                self._refs["updated"].configure(
                    text=f"Updated\n{datetime.datetime.now().strftime('%H:%M')}")

                days = weather.get("forecast", [])
                for i, day in enumerate(days[:3]):
                    self._refs[f"fcast_icon_{i}"].configure(text=day["emoji"])
                    self._refs[f"fcast_day_{i}"].configure(
                        text=["Today", "Tomorrow"][i] if i < 2 else
                        (datetime.datetime.now() +
                         datetime.timedelta(days=2)).strftime("%A"))
                    self._refs[f"fcast_cond_{i}"].configure(text=day["description"])
                    self._refs[f"fcast_kwh_{i}"].configure(
                        text=str(day.get("day_kwh", "--")))

                hourly_kwh = weather.get("hourly_kwh", [0.0]*24)
                forecast   = weather.get("forecast", [])
                if forecast:
                    self._update_tea_time(hourly_kwh)
                    self._update_forecast_chart(hourly_kwh)

            if live:
                self._refs["pv_power"].configure(text=f"{live['pv_power_kw']}")
                self._update_daily_stats(live, store)

            if store:
                best_day = snap.get("best_day", {})
                bd_kwh  = best_day.get("kwh", 0.0)
                bd_date = best_day.get("date")
                if bd_kwh:
                    self._refs["best_day_kwh"].configure(text=f"{bd_kwh:.2f}")
                    if bd_date:
                        d = datetime.date.fromisoformat(bd_date)
                        self._refs["best_day_date"].configure(
                            text=d.strftime("%d %b").lstrip("0"))
                else:
                    self._refs["best_day_kwh"].configure(text="--")
                    self._refs["best_day_date"].configure(text="")

                if self.lt_panel:
                    self.lt_panel.update_data(store)

                history = store.get("daily_history", [])
                if history:
                    last7    = history[-7:]
                    avg_gen  = sum(d["generation_kwh"] for d in last7) / 7
                    avg_exp  = sum(d["export_kwh"] for d in last7) / 7
                    avg_earn = avg_exp * config.OCTOPUS_SEG_RATE
                    self._refs["avg_gen"].configure(text=f"{avg_gen:.1f} kWh")
                    self._refs["avg_export"].configure(
                        text=f"{avg_exp:.1f} kWh · £{avg_earn:.2f}")

        self.after(config.REFRESH_SECONDS * 1000, self._update_ui)

    def _update_daily_stats(self, live, store):
        """Update generated/exported/earnings based on today or week toggle."""
        if self._daily_mode == "today":
            self._refs["generated"].configure(text=f"{live['pv_day_kwh']} kWh")
            self._refs["load_pct"].configure(text=f"{live['load_satisfied_pct']}%")
            today_str = datetime.date.today().isoformat()
            today_rec = next(
                (d for d in store.get("daily_history", []) if d["date"] == today_str), None)
            if today_rec and today_rec.get("export_kwh", 0.0):
                self._refs["exported"].configure(
                    text=f"{today_rec['export_kwh']:.2f} kWh")
                self._refs["earnings"].configure(
                    text=f"£{today_rec['export_earnings_gbp']:.2f}")
            else:
                self._refs["exported"].configure(text="--")
                self._refs["earnings"].configure(text="--")
        else:
            totals = data_store.get_period_totals("week")
            self._refs["generated"].configure(text=f"{totals['generation_kwh']:.1f} kWh")
            self._refs["load_pct"].configure(text="--")
            self._refs["exported"].configure(text=f"{totals['export_kwh']:.1f} kWh")
            self._refs["earnings"].configure(text=f"£{totals['earnings_gbp']:.2f}")

    def _update_forecast_chart(self, hourly_kwh):
        ax     = self._refs["chart_ax"]
        canvas = self._refs["chart_canvas"]

        ax.cla()
        ax.set_facecolor("#f2f4f3")

        now    = datetime.datetime.now().hour
        colors = ["#3ec9b6" if h >= now else "#a8e8dc" for h in range(24)]

        ax.bar(range(24), hourly_kwh, color=colors, width=0.8, alpha=0.7)
        ax.set_xlim(-0.5, 23.5)
        ax.set_ylim(0, 3.2)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["00:00", "06:00", "12:00", "18:00", "23:00"],
                           fontsize=7, color="#8aa8a2")
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#dde8e5")
        ax.tick_params(axis="x", length=0)
        ax.figure.tight_layout(pad=0.3)
        canvas.draw()

    def _update_tea_time(self, hourly_kwh):
        now     = datetime.datetime.now().hour
        peak_kw = 3.09

        # Only consider remaining hours with meaningful generation
        remaining = [
            (hour, hourly_kwh[hour])
            for hour in range(now, 20)
            if hour < len(hourly_kwh) and hourly_kwh[hour] > 0.1
        ]

        top3 = sorted(remaining, key=lambda x: -x[1])[:3]
        top3.sort(key=lambda x: x[0])

        def fmt(h):
            suffix = "am" if h < 12 else "pm"
            h12 = h if h <= 12 else h - 12
            return f"{h12}{suffix}"

        if not top3:
            for slot_refs in self._refs["tea_slots"]:
                slot_refs["time"].configure(text="No significant generation remaining")
                slot_refs["bar"].place(relwidth=0)
                slot_refs["kwh"].configure(text="")
            return

        for j, slot_refs in enumerate(self._refs["tea_slots"]):
            if j < len(top3):
                hour, est_kwh = top3[j]
                pct = min(1.0, est_kwh / peak_kw)
                slot_refs["time"].configure(text=f"{fmt(hour)} – {fmt(hour+1)}")
                slot_refs["bar"].place(relx=0, rely=0, relwidth=pct, relheight=1)
                slot_refs["kwh"].configure(text=f"~{est_kwh} kWh")
            else:
                slot_refs["time"].configure(text="")
                slot_refs["bar"].place(relwidth=0)
                slot_refs["kwh"].configure(text="")

    # ------------------------------------------------------------------ #
    # Toggle handlers                                                      #
    # ------------------------------------------------------------------ #

    def _show_today(self):
        self._daily_mode = "today"
        self.btn_today.configure(
            fg_color=TEAL, text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_week.configure(
            fg_color=CARD, text_color=MUTED,
            font=ctk.CTkFont(size=11))
        self._update_ui()

    def _show_week(self):
        self._daily_mode = "week"
        self.btn_week.configure(
            fg_color=TEAL, text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_today.configure(
            fg_color=CARD, text_color=MUTED,
            font=ctk.CTkFont(size=11))
        self._update_ui()

    # ------------------------------------------------------------------ #
    # Windows always-on-bottom                                            #
    # ------------------------------------------------------------------ #

    def _push_to_bottom(self):
        try:
            import win32gui
            import win32con
            hwnd = _hwnd(self)
            if hwnd:
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                    win32con.SWP_NOACTIVATE)
        except Exception:
            pass
        self.after(1000, self._push_to_bottom)


if __name__ == "__main__":
    app = SolarWidget()
    app.mainloop()