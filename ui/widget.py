# ui/widget.py
import datetime
import customtkinter as ctk
import ctypes
import sys
import config

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


class SolarWidget(ctk.CTk):

    def __init__(self, refresher=None):
        super().__init__()
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        self.refresher = refresher
        self._refs = {}

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

        # --- Start live update loop ---
        self.after(1000, self._update_ui)

        # --- Push to bottom of Z-order ---
        self.after(200, self._push_to_bottom)

    def _pad(self, height=4):
        ctk.CTkFrame(self.scroll, fg_color=BG, height=height).pack(fill="x")

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
            row, text="--",
            font=ctk.CTkFont(size=24), text_color=TEXT
        )
        self._refs["weather_icon"].pack(side="left")

        temp_frame = ctk.CTkFrame(row, fg_color=CARD)
        temp_frame.pack(side="left", padx=8)

        self._refs["temp"] = ctk.CTkLabel(
            temp_frame, text="--°C",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT
        )
        self._refs["temp"].pack(anchor="w")

        self._refs["condition"] = ctk.CTkLabel(
            temp_frame, text="Loading...",
            font=ctk.CTkFont(size=10), text_color=MUTED
        )
        self._refs["condition"].pack(anchor="w")

        self._refs["updated"] = ctk.CTkLabel(
            row, text="Updated\n--:--",
            font=ctk.CTkFont(size=10), text_color=MUTED, justify="right"
        )
        self._refs["updated"].pack(side="right")

        self._pad()

    def _build_realtime(self):
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
        self._refs["pv_power"] = ctk.CTkLabel(
            gen_row, text="--",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=TEAL
        )
        self._refs["pv_power"].pack(side="left")
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
        self._refs["best_hour"] = ctk.CTkLabel(
            bh_row, text="--",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=AMBER
        )
        self._refs["best_hour"].pack(side="left")
        ctk.CTkLabel(
            bh_row, text=" kWh",
            font=ctk.CTkFont(size=12), text_color=MUTED
        ).pack(side="left", pady=(4, 0))

        self._pad()

    def _build_daily(self):
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

        # Stats card
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

            icon = ctk.CTkLabel(
                row, text=emoji, font=ctk.CTkFont(size=26))
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
        tea.pack(fill="x", padx=10, pady=(0, 12))

        header = ctk.CTkFrame(tea, fg_color=CARD)
        header.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            header, text="☕", font=ctk.CTkFont(size=20)
        ).pack(side="left")
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
                corner_radius=6, border_width=1, border_color=TEAL_BORDER
            )
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

        ctk.CTkFrame(tea, fg_color=CARD, height=4).pack()

    # ------------------------------------------------------------------ #
    # Live data update                                                     #
    # ------------------------------------------------------------------ #

    def _update_ui(self):
        if self.refresher:
            snap    = self.refresher.snapshot()
            live    = snap.get("live")
            weather = snap.get("weather")
            store   = snap.get("store", {})

            # --- Weather ---
            if weather and not weather.get("error"):
                self._refs["weather_icon"].configure(
                    text=weather["emoji"])
                self._refs["temp"].configure(
                    text=f"{weather['temperature']}°C")
                self._refs["condition"].configure(
                    text=f"{weather['description']} · "
                         f"Wind {weather['wind_kph']} km/h")
                self._refs["updated"].configure(
                    text=f"Updated\n"
                         f"{datetime.datetime.now().strftime('%H:%M')}")

                # Forecast cards
                days = weather.get("forecast", [])
                for i, day in enumerate(days[:3]):
                    est = round(day["sunshine_hrs"] * 0.85, 1)
                    self._refs[f"fcast_icon_{i}"].configure(
                        text=day["emoji"])
                    self._refs[f"fcast_day_{i}"].configure(
                        text=["Today", "Tomorrow"][i] if i < 2 else
                        (datetime.datetime.now() +
                         datetime.timedelta(days=2)).strftime("%A"))
                    self._refs[f"fcast_cond_{i}"].configure(
                        text=day["description"])
                    self._refs[f"fcast_kwh_{i}"].configure(
                        text=str(est))

                # Tea time
                forecast = weather.get("forecast", [])
                if forecast:
                    self._update_tea_time(forecast[0])

            # --- Live data ---
            if live:
                self._refs["pv_power"].configure(
                    text=f"{live['pv_power_kw']}")
                self._refs["generated"].configure(
                    text=f"{live['pv_day_kwh']} kWh")
                self._refs["load_pct"].configure(
                    text=f"{live['load_satisfied_pct']}%")

            # --- Store ---
            if store:
                earnings = store.get("cumulative_export_earnings_gbp", 0.0)
                self._refs["earnings"].configure(text=f"£{earnings:.2f}")
                best = store.get("best_hour_kwh", 0.0)
                self._refs["best_hour"].configure(
                    text=f"{best:.2f}" if best else "--")

        self.after(config.REFRESH_SECONDS * 1000, self._update_ui)

    def _update_tea_time(self, today_forecast):
        """
        Show best 3 remaining hours today based on expected generation.
        Bar represents % of peak system capacity (3.09kW = 3.09kWh max/hour).
        """
        now = datetime.datetime.now().hour
        sunshine = today_forecast.get("sunshine_hrs", 0)
        peak_kw = 3.09

        remaining = []
        for hour in range(now, 20):
            dist = abs(hour - 13)
            weight = max(0, 1 - (dist / 7))
            est_kwh = round(weight * (sunshine / 8) * peak_kw, 2)
            if est_kwh > 0.1:
                remaining.append((hour, est_kwh))

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