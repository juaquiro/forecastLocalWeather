# Mountain Forecast (Pyto + Toga)

A tiny **offline** hiking helper for iOS (via **Pyto**) that lets you log time-stamped readings—**altitude, temperature, dew point, humidity**—and shows a simple **trend**: `BETTER`, `STABLE`, or `WORSE`.

Sessions are kept only in memory; when you start a **New session** (or **Exit**), the app writes a plain-text log to your device and clears the in-memory data.

---

## Features

- **Completely offline** once installed in Pyto.
- **Simple UI** (Toga) with:
  - inputs for Altitude (m), Temp (°C), Dew-pt (°C), Humidity (%)
  - **Add reading**, **New session**, **Exit** buttons
- **Session logging** to `~/Documents/MountainForecastLogs/` (inside Pyto’s sandbox).
- **No persistence** other than exported log files.
- **Pure-Python algorithm** you can tweak easily.

---

## How the trend is computed (current heuristic)

Let `spread = temperature − dew_point`. Compare spread at the **first** reading vs the **latest**:

- If the spread **widens** by more than 2 °C → **BETTER** (drier air, likely clearing)
- If it **narrows** by more than 2 °C → **WORSE** (moistening, possible clouding)
- Otherwise → **STABLE**

You can change the threshold and logic in `forecast_app/forecast.py`.

---

## Repository layout

```
mountain-forecast/
├─ README.md
├─ LICENSE
├─ .gitignore                  # include logs/ so local trail data isn’t committed
├─ requirements.txt            # optional (for desktop dev/testing)
├─ forecast_app/
│   ├─ __init__.py             # (optional, can be empty)
│   ├─ forecast_ui.py          # ← RUN THIS in Pyto
│   ├─ forecast.py             # trend algorithm (pure functions)
│   └─ forecast_logger.py      # log path + save_log()
└─ logs/                       # created at runtime; ignored by git
```

> Tip: If you’re using Pyto only, `requirements.txt` can be empty. On desktop, add `toga` and `pytest` as needed.

---

## Running on iPhone/iPad with Pyto

1. **Install Pyto** from the App Store.
2. Copy the `forecast_app/` folder into **On My iPhone › Pyto** (AirDrop, iCloud Drive, or Working Copy).
3. Open **`forecast_app/forecast_ui.py`** and tap **Run**.
4. Enter four numbers, tap **Add reading**; repeat as needed.  
   Tap **New session** to save the current log and start over.  
   Tap **Exit** to save and quit immediately.

**Log files** are written to:

```
On My iPhone / Pyto / Documents / MountainForecastLogs /
```

Each file is named like `session_YYYYMMDD_HHMMSS.txt` with CSV-style rows:

```
# time_iso,alt_m,temp_C,dew_C,humidity_%
2025-08-02T15:20:11.527340,1500,10,7,85
2025-08-02T15:25:30.104822,1550,9,6,83
```

---

## Running on desktop (optional)

```bash
# from the repo root
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt   # add toga, pytest here if you want
python -m forecast_app.forecast_ui
```

> Toga backends vary by platform; if you don’t want a UI on desktop, you can still develop and unit-test the algorithm in `forecast_app/forecast.py`.

---

## Editing the algorithm

Open `forecast_app/forecast.py` and modify:

```python
def classify(delta, thr=2.0): ...
def forecast(session): ...
```

`session` is a list of dicts like:

```python
{"t": datetime, "alt": float, "temp": float, "dew": float, "rh": float}
```

Because the algorithm is **pure**, you can unit-test it easily and keep the UI stable.

---

## Git on iOS (Pyto)

Pyto doesn’t ship a `git` binary. Easiest options:

- **Working Copy** (App Store): clone/pull/push there, then expose the repo to Pyto via **External Folder**.
- Or use a pure-Python library (e.g., `dulwich`) if you need scripted Git operations inside Pyto.

---

## Troubleshooting

- **PermissionError when saving logs**  
  Logs are written to `Path.home()/Documents/MountainForecastLogs`, which is writable in Pyto’s sandbox. If you moved the app elsewhere and hit errors, put it back under *On My iPhone › Pyto*.

- **Exit button is slow**  
  We close the main window and call `sys.exit(0)` for immediate shutdown.

- **What’s my working directory in Pyto’s Terminal?**  
  `import os, pathlib; os.getcwd(); pathlib.Path.cwd()`  
  (Running a script sets cwd to the script’s folder; the Terminal starts in `~/Documents`.)

---

## Roadmap / ideas

- Optional graph (matplotlib) of readings over time.
- Alternate heuristics (pressure tendency, lapse rate).
- Export last session to clipboard / share sheet.
- BeeWare packaging to a distributable iOS app if we outgrow Pyto.

---

## Contributing

1. Fork → create a feature branch.
2. Keep UI changes in `forecast_ui.py`, algorithmic changes in `forecast.py`.
3. Add/update tests if you add new logic (optional test suite not included here).
4. Open a PR.

---

## License

Choose a license (e.g., MIT) and place it in `LICENSE`.
