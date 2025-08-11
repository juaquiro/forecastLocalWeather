# config_loader.py  –  TOML config for Python 3.10 (Pyto)
from __future__ import annotations
from pathlib import Path
import io

# Try stdlib tomllib (3.11+) then fall back to tomli (vendor it if needed)
try:                                     # Py 3.11+
    import tomllib as _toml
except Exception:                        # Py 3.10 → needs tomli
    import tomli as _toml                # pip install tomli, or vendor tomli.py

CONFIG_DIR = Path.home() / "Documents" / "MountainForecastConfig"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_DEFAULT_TOML = """\
[app]
# Where logs are written (relative paths resolved under ~/Documents)
log_dir = "MountainForecastLogs"

[forecast.constants]
dew_spread_threshold = 2.0              # °C widening to call BETTER
min_samples_for_forecast = 2            # Require at least 2 readings

[ml]
enabled = false
model_path = "models/naive.joblib"      # Example; not required for Pyto
desc = "Toggle/use ML-based trend; if disabled, use heuristic."

[ml.params]
window_minutes = 30
min_points = 6

# Optional: central place for displayable descriptions of simple keys
[descriptions.forecast.constants]
dew_spread_threshold = "Minimum widening (°C) to signal BETTER"
min_samples_for_forecast = "Minimum readings before showing a trend"

# -------------------------------------------------------------------
# U.S. Standard Atmosphere (troposphere) constants
# Units are explicit; convert as needed in code.
# -------------------------------------------------------------------
[atmosphere.T0]
value = 288.15
unit  = "K"
desc  = "Reference temperature at sea level (0 km)."

[atmosphere.L0]
value = -6.5
unit  = "K/km"
desc  = "Temperature lapse rate in the troposphere."

[atmosphere.P0]
value = 101325
unit  = "Pa"
desc  = "Reference pressure at sea level."

[atmosphere.R]
value = 8.31432e3
unit  = "N·m/(kmol·K)"
desc  = "Universal gas constant (per kmol)."

[atmosphere.M0]
value = 28.9644
unit  = "kg/kmol"
desc  = "Molar mass of dry air."

[atmosphere.H0]
value = 0.0
unit  = "km"
desc  = "Reference geopotential height."
"""

def ensure_exists() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(_DEFAULT_TOML, encoding="utf-8")

def load_config() -> dict:
    """
    Returns a nested dict from config.toml.
    If the file doesn't exist, writes defaults first.
    """
    ensure_exists()
    with CONFIG_FILE.open("rb") as f:
        return _toml.load(f)

def get(d: dict, dotted: str, default=None):
    """Get nested value by dotted path, e.g. 'forecast.constants.dew_spread_threshold'."""
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def path_in_docs(*parts: str) -> Path:
    """Resolve a path under ~/Documents (useful for model files, logs)."""
    return Path.home() / "Documents" / Path(*parts)

def atmosphere_constants_SI(cfg: dict) -> dict:
    atm = cfg.get("atmosphere", {})
    def v(k, d): return float(atm.get(k, {}).get("value", d))
    T0_K = v("T0", 288.15)
    L0_K_per_m = v("L0", -6.5) / 1000.0          # K/km → K/m
    P0_Pa = v("P0", 101325.0)
    R_J_per_molK = v("R", 8.31432e3) / 1000.0    # per kmol → per mol
    M0_kg_per_mol = v("M0", 28.9644) / 1000.0    # per kmol → per mol
    H0_m = v("H0", 0.0) * 1000.0                 # km → m
    return dict(T0_K=T0_K, L0_K_per_m=L0_K_per_m, P0_Pa=P0_Pa,
                R_J_per_molK=R_J_per_molK, M0_kg_per_mol=M0_kg_per_mol, H0_m=H0_m)
