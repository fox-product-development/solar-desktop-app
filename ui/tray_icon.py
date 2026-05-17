# ui/tray_icon.py
"""
System tray icon for Solar Monitor.
Provides a notification-area icon with a right-click menu.
Uses pystray (install: pip install pystray) + Pillow (already required).
"""

import threading
import logging
from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

_ICON_SIZE = 64


def _make_icon_image(generating: bool = True) -> Image.Image:
    """
    Draw a simple solar-panel icon programmatically.
    Green teal when generating, grey when idle/unknown.
    Returns a 64×64 RGBA PIL Image.
    """
    img  = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    panel_colour = (62, 201, 182, 255) if generating else (150, 160, 158, 255)  # teal / grey
    ray_colour   = (240, 165, 0, 255)   # amber

    # Sun rays (4 short lines from centre-top area)
    cx, cy = 44, 16
    for dx, dy in [(-8, -8), (0, -10), (8, -8), (10, 0)]:
        draw.line(
            [(cx + dx // 2, cy + dy // 2), (cx + dx, cy + dy)],
            fill=ray_colour, width=2
        )

    # Sun circle
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=ray_colour)

    # Solar panel body — 3×2 grid of cells
    px, py, pw, ph = 6, 22, 44, 30
    draw.rounded_rectangle([px, py, px + pw, py + ph],
                           radius=3, fill=panel_colour)

    # Cell grid lines (white, semi-transparent)
    cell_w = pw // 3
    cell_h = ph // 2
    grid_colour = (255, 255, 255, 80)
    for col in range(1, 3):
        x = px + col * cell_w
        draw.line([(x, py + 1), (x, py + ph - 1)], fill=grid_colour, width=1)
    draw.line([(px + 1, py + cell_h), (px + pw - 1, py + cell_h)],
              fill=grid_colour, width=1)

    # Panel border
    draw.rounded_rectangle([px, py, px + pw, py + ph],
                           radius=3, outline=(255, 255, 255, 120), width=1)

    # Stand / mount
    draw.rectangle([26, 52, 30, 60], fill=(100, 120, 118, 255))
    draw.rectangle([18, 58, 38, 62], fill=(100, 120, 118, 255))

    return img


class TrayIcon:
    """
    Wraps a pystray icon. Runs in its own daemon thread so it doesn't
    block the tkinter main loop.

    Usage:
        tray = TrayIcon(app_widget)
        tray.start()
        # later:
        tray.stop()
    """

    def __init__(self, widget):
        self._widget = widget   # SolarWidget instance
        self._icon   = None
        self._thread = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start the tray icon in a background thread."""
        try:
            import pystray
        except ImportError:
            log.warning("pystray not installed — system tray icon unavailable. "
                        "Run: pip install pystray")
            return

        image = _make_icon_image(generating=True)

        menu = pystray.Menu(
            pystray.MenuItem("Solar Monitor", self._noop, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show / Hide", self._toggle_visibility,
                             default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon(
            name="solar_monitor",
            icon=image,
            title="Solar Monitor",
            menu=menu,
        )

        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="TrayIconThread",
        )
        self._thread.start()
        log.info("System tray icon started.")

    def stop(self):
        """Remove the tray icon cleanly."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def set_generating(self, generating: bool):
        """Update the icon colour to reflect current generation state."""
        if self._icon:
            try:
                self._icon.icon = _make_icon_image(generating=generating)
            except Exception:
                pass

    def set_tooltip(self, text: str):
        """Update the hover tooltip (shown on Windows, limited on Linux/macOS)."""
        if self._icon:
            try:
                self._icon.title = text
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Private callbacks (called from pystray's thread)                    #
    # ------------------------------------------------------------------ #

    def _noop(self):
        pass

    def _toggle_visibility(self):
        """Show or hide the main widget. Must marshal back to tkinter thread."""
        try:
            w = self._widget
            if w.winfo_viewable():
                w.after(0, w.withdraw)
            else:
                w.after(0, w.deiconify)
                w.after(50, w._push_to_bottom)   # keep it behind other windows
        except Exception as exc:
            log.debug("Toggle visibility failed: %s", exc)

    def _quit(self):
        """Cleanly shut down the whole application."""
        try:
            self._widget.after(0, self._widget.destroy)
        except Exception:
            pass
        self.stop()