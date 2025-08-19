# Toga UI: wires inputs/buttons to the forecast + logging utilities.

import os, sys
import datetime as dt
import toga
from toga.style.pack import COLUMN, ROW, LEFT, Pack, CENTER
from toga.colors import rgb, WHITE, BLACK

WD_Folder = os.path.dirname(os.path.abspath(__file__))   # Working Dir folder of forecast_ui.py
PARENT_Folder = os.path.dirname(WD_Folder)                      # repo root (one level up)

# 1) Make the package importable no matter the current working dir:
if PARENT_Folder not in sys.path:
    sys.path.insert(0, PARENT_Folder)

# 2) (Optional but helpful) make the working directory the UI file's folder:
os.chdir(WD_Folder)

# Now absolute, package-style imports will work reliably:
from forecast_app.forecast import forecast
from forecast_app.forecast_logger import save_log

# LOAD CONFIG
from forecast_app.config_loader import load_config, get, path_in_docs, atmosphere_constants_SI
cfg = load_config()
atm = atmosphere_constants_SI(cfg)

# Examples:
threshold = get(cfg, "forecast.constants.dew_spread_threshold", 2.0)
need_n    = get(cfg, "forecast.constants.min_samples_for_forecast", 2)

log_dir = path_in_docs(get(cfg, "app.log_dir", "MountainForecastLogs"))
# Pass `threshold` into your algorithm; use `log_dir` in your logger.

# If you want to show help text somewhere:
desc = get(cfg, "descriptions.forecast.constants.dew_spread_threshold")


def build(app):
    session = []  # lives in this closure

    # --- palette (chosen for good visibility on iOS) ---
    PAGE_BG         = rgb(245, 247, 250)  # light gray app background
    OUTLINE_PRIMARY = rgb(37, 99, 235)    # blue outline
    OUTLINE_SECOND  = rgb(107, 114, 128)  # gray outline
    OUTLINE_DANGER  = rgb(220, 38, 38)    # red outline
    BANNER_NEUTRAL  = rgb(31, 41, 55)     # dark slate
    BANNER_GOOD     = rgb(16, 185, 129)   # green
    BANNER_BAD      = rgb(220, 38, 38)    # red

    # -- widgets
    alt_in  = toga.TextInput(placeholder="Altitude (m)")
    temp_in = toga.TextInput(placeholder="Temp (°C)")
    dew_in  = toga.TextInput(placeholder="Dew-pt (°C)")
    rh_in   = toga.TextInput(placeholder="Humidity (%)")

    # Bold, centered banner label for the trend
    trend_lbl = toga.Label(
        "No data yet",
        style=Pack(
            padding_top=12, padding_bottom=12, padding_left=10, padding_right=10,
            background_color=BANNER_NEUTRAL, color=WHITE,
            text_align=CENTER, font_size=18
        )
    )

    # Helper: a visible 'outlined' button constructed from Boxes.
    # The inner Button provides the tap behavior; the colored outer Box is the border.
    def outlined_button(text, on_press, border_color, *, page_bg, flex=1, left_pad=0, right_pad=0):
        wrapper = toga.Box(style=Pack(direction=ROW, flex=flex,
                                      padding_left=left_pad, padding_right=right_pad))
        border = toga.Box(style=Pack(background_color=border_color, padding=2, flex=1))
        fill   = toga.Box(style=Pack(background_color=page_bg, flex=1))
        btn    = toga.Button(
            text,
            on_press=on_press,
            style=Pack(
                color=border_color,
                padding_top=10, padding_bottom=10,
                padding_left=12, padding_right=12
            )
        )
        fill.add(btn)
        border.add(fill)
        wrapper.add(border)
        return wrapper

    # -- callbacks
    def add_reading(widget):
        try:
            reading = {
                "t":   dt.datetime.now(),
                "alt": float(alt_in.value),
                "temp": float(temp_in.value),
                "dew":  float(dew_in.value),
                "rh":   float(rh_in.value),
            }
        except ValueError:
            trend_lbl.text = "Fill all 4 numbers"
            trend_lbl.style.update(background_color=BANNER_NEUTRAL)
            return
        session.append(reading)

        # update the banner color when you compute the trend
        trend = forecast(session)
        trend_lbl.text = f"Trend: {trend}   ({len(session)} readings)"
        if trend == "BETTER":
            trend_lbl.style.update(background_color=BANNER_GOOD)
        elif trend == "WORSE":
            trend_lbl.style.update(background_color=BANNER_BAD)
        else:  # "STABLE" or "NEED MORE DATA"
            trend_lbl.style.update(background_color=BANNER_NEUTRAL)

    def new_session(widget):
        log = save_log(session, app.main_window)
        session.clear()
        for box in (alt_in, temp_in, dew_in, rh_in):
            box.value = ""
        trend_lbl.text = "New session started" + (f" – saved {log}" if log else "")
        trend_lbl.style.update(background_color=BANNER_NEUTRAL)

    def quit_app(widget):
        save_log(session, app.main_window)
        # Close immediately (snappier than app.exit() alone):
        try:
            app.main_window.close()
        finally:
            sys.exit(0)

    # -- tiny layout helper
    def row(inp, caption):
        r = toga.Box(style=Pack(direction=ROW, padding=4))
        r.add(inp)
        r.add(toga.Label(caption, style=Pack(padding_left=8, width=110, text_align=LEFT)))
        inp.style.update(flex=1)
        return r

    # -- assemble UI
    box = toga.Box(style=Pack(direction=COLUMN, padding=10, background_color=PAGE_BG))
    for inp, cap in [
        (alt_in,  "Altitude (m)"),
        (temp_in, "Temp (°C)"),
        (dew_in,  "Dew-pt (°C)"),
        (rh_in,   "Humidity (%)"),
    ]:
        box.add(row(inp, cap))

    # --- buttons row: outlined buttons ---
    buttons = toga.Box(style=Pack(direction=ROW, padding=8))
    buttons.add(outlined_button("Add reading", add_reading, OUTLINE_PRIMARY, page_bg=PAGE_BG, right_pad=5))
    buttons.add(outlined_button("New session", new_session, OUTLINE_SECOND,  page_bg=PAGE_BG, left_pad=5))
    box.add(buttons)

    # --- exit as full-width outlined button ---
    exit_row = toga.Box(style=Pack(direction=ROW, padding_left=8, padding_right=8, padding_bottom=8))
    exit_row.add(outlined_button("Exit", quit_app, OUTLINE_DANGER, page_bg=PAGE_BG, flex=1))
    box.add(exit_row)

    # Trend banner at the bottom
    box.add(trend_lbl)
    return box


def main():
    return toga.App("Mountain Forecast", "org.example.mountain_forecast", startup=build)


if __name__ == "__main__":
    main().main_loop()
