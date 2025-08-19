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

    # --- color palette for buttons (good contrast on iOS) ---
    BTN_PRIMARY_BG = rgb(37, 99, 235)   # blue
    BTN_SECOND_BG  = rgb(107, 114, 128) # gray
    BTN_DANGER_BG  = rgb(220, 38, 38)   # red
    BANNER_NEUTRAL = rgb(31, 41, 55)     # dark slate
    BANNER_GOOD    = rgb(16,185,129)     # green
    BANNER_BAD     = rgb(220, 38, 38)    # red
    BTN_TXT        = WHITE
    PAGE_BG = rgb(245, 247, 250)  # light gray that makes system text-buttons stand out


    # -- widgets
    alt_in  = toga.TextInput(placeholder="Altitude (m)")
    temp_in = toga.TextInput(placeholder="Temp (°C)")
    dew_in  = toga.TextInput(placeholder="Dew-pt (°C)")
    rh_in   = toga.TextInput(placeholder="Humidity (%)")
    
    # create a bold, centered banner label
    trend_lbl = toga.Label(
    "No data yet",
    style=Pack(
        padding_top=12, padding_bottom=12, padding_left=10, padding_right=10,
        background_color=BANNER_NEUTRAL, color=BTN_TXT,
        text_align=CENTER, font_size=18
        )
    )

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

    # --- buttons row ---
    buttons = toga.Box(style=Pack(direction=ROW, padding=8))
    add_btn = toga.Button(
        "Add reading",
        on_press=add_reading,
        style=Pack(
            flex=1, padding=10, padding_right=5,
            background_color=BTN_PRIMARY_BG, color=BTN_TXT
        ),
    )
    new_btn = toga.Button(
        "New session",
        on_press=new_session,
        style=Pack(
            flex=1, padding=10, padding_left=5,
            background_color=BTN_SECOND_BG, color=BTN_TXT
        ),
    )
    buttons.add(add_btn)
    buttons.add(new_btn)
    box.add(buttons)


    # --- exit button as a full-width danger button ---
    exit_btn = toga.Button(
        "Exit",
        on_press=quit_app,
        style=Pack(
            padding=10, background_color=BTN_DANGER_BG, color=BTN_TXT
        ),
    )
    box.add(exit_btn)


    box.add(trend_lbl)
    return box

def main():
    return toga.App("Mountain Forecast", "org.example.mountain_forecast", startup=build)

if __name__ == "__main__":
    main().main_loop()
