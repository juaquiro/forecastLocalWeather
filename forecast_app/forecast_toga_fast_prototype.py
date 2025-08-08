"""
mountain_forecast_toga.py
AQ 8AUG25 generado con ChatGPT-4
A simple Toga app to log mountain weather data
---------------------------------------------------------------
• Records readings → TREND = BETTER / STABLE / WORSE.
• When you tap “New session” or “Exit” the current log is
  written to  ~/Documents/Forecast_App_Logs/session_YYYYMMDD_HHMMSS.txt
  (a folder the sandbox can always write to).
"""

import datetime as dt
from pathlib import Path
import toga
from toga.style.pack import COLUMN, ROW, LEFT, Pack

# ---------- safe log directory inside the sandbox --------------
LOG_DIR = Path.home() / "Documents" / "Forecast_App_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------- forecast logic -------------------------------------
def classify(delta, thr=2.0):
    if delta > thr:
        return "BETTER"
    elif delta < -thr:
        return "WORSE"
    return "STABLE"


def forecast(session):
    if len(session) < 2:
        return "NEED MORE DATA"
    s0 = session[0]["temp"] - session[0]["dew"]
    sN = session[-1]["temp"] - session[-1]["dew"]
    return classify(sN - s0)


# ---------- logging helper -------------------------------------
def save_log(session, window):
    """Write one finished session. Return filename or None."""
    if not session:
        return None

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = LOG_DIR / f"session_{ts}.txt"
    try:
        with fname.open("w", encoding="utf-8") as f:
            f.write("# time_iso,alt_m,temp_C,dew_C,humidity_%\n")
            for r in session:
                f.write(
                    f'{r["t"].isoformat()},'
                    f'{r["alt"]},{r["temp"]},{r["dew"]},{r["rh"]}\n'
                )
    except (PermissionError, OSError) as err:
        # Warn the user but keep the app alive
        window.error_dialog(
            "Log-file error",
            f"Could not save log:\n{err}\n\n"
            "Tip: move the script into ‘On My iPhone/Pyto’ "
            "or give Pyto access to its folder."
        )
        return None

    return fname.name  # success


# ---------- UI build -------------------------------------------
def build(app):
    session = []                                     # lives in closure

    # widgets
    alt_in, temp_in, dew_in, rh_in = (toga.TextInput() for _ in range(4))
    trend_lbl = toga.Label("No data yet", style=Pack(padding_top=10))

    # callbacks
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
        trend_lbl.text = f"Trend: {forecast(session)}   ({len(session)} readings)"

    def new_session(widget):
        log = save_log(session, app.main_window)
        session.clear()
        for box in (alt_in, temp_in, dew_in, rh_in):
            box.value = ""
        trend_lbl.text = (
            "New session started" + (f" – saved {log}" if log else "")
        )

    def quit_app(widget):
        save_log(session, app.main_window)
        app.exit()

    # layout helpers
    def row(inp, caption):
        r = toga.Box(style=Pack(direction=ROW, padding=4))
        r.add(inp)
        r.add(
            toga.Label(
                caption, style=Pack(padding_left=8, width=110, text_align=LEFT)
            )
        )
        inp.style.update(flex=1)
        return r

    # assemble
    box = toga.Box(style=Pack(direction=COLUMN, padding=10))
    for inp, cap in [
        (alt_in, "Altitude (m)"),
        (temp_in, "Temp (°C)"),
        (dew_in, "Dew-pt (°C)"),
        (rh_in, "Humidity (%)"),
    ]:
        box.add(row(inp, cap))

    btns = toga.Box(style=Pack(direction=ROW, padding=8))
    btns.add(
        toga.Button(
            "Add reading", on_press=add_reading, style=Pack(flex=1, padding_right=5)
        )
    )
    btns.add(
        toga.Button(
            "New session", on_press=new_session, style=Pack(flex=1, padding_left=5)
        )
    )
    box.add(btns)
    box.add(toga.Button("Exit", on_press=quit_app, style=Pack(padding=8)))
    box.add(trend_lbl)
    return box


def main():
    return toga.App(
        "Mountain Forecast", "org.example.mountain_forecast", startup=build
    )


if __name__ == "__main__":
    main().main_loop()
