# Centralized logging: write finished sessions to a safe, writable folder.

import datetime as dt
from pathlib import Path

# Always-writable app sandbox path in Pyto:
LOG_DIR = Path.home() / "Documents" / "Forecast_App_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def save_log(session, window=None):
    """
    Write current session to LOG_DIR. Returns filename (str) or None.
    If window (toga.Window) is provided, shows a dialog on error.
    """
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
        return fname.name
    except (PermissionError, OSError) as err:
        if window is not None:
            try:
                window.error_dialog("Log-file error", f"Could not save log:\n{err}")
            except Exception:
                pass
        else:
            print("Log-file error:", err)
        return None

