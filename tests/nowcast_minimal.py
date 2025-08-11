
"""
nowcast_minimal.py
-------------------
A minimal, source-driven nowcasting rule engine for alpine hiking using only:
Temperature (T, °C), Dew Point (Td, °C), Relative Humidity (RH, %),
Altitude (H, m), and measured Barometric Pressure (P_meas, hPa).
Optionally, a measured cloud-base (LCL_meas, m above mean sea level) can be provided.

It outputs a categorical forecast: "Better" / "Stable" / "Worse",
an ETA window for the expected change, and a comparison between
estimated LCL (from T and Td) and any measured LCL if available.

Pressure-altitude compensation uses the barometric formula for the troposphere (0–11 km):

    P(H) = P0 * [ T0 / (T0 + L0 * H) ]^( (g * M0) / (R * L0) )
         = P0 * [ 1 + (L0 * H) / T0 ]^( - (g * M0) / (R * L0) )

where:
  - P(H)  : static pressure at geometric altitude H (Pa)
  - P0    : static pressure at 0 m (sea level) (Pa)
  - T0    : standard temperature at 0 m (K) [288.15 K]
  - L0    : standard temperature lapse rate in the troposphere (K/m). NOTE: in the troposphere L0 = -0.0065 K/m
  - g     : standard gravity (m/s^2) [9.80665 m/s^2]
  - M0    : molar mass of Earth's air (kg/mol) [0.0289644 kg/mol]
  - R     : universal gas constant (J/(mol·K)) [8.3144598 J/(mol·K)]

We use the formula to adjust pressures measured at a changing hiking altitude
back to a fixed reference altitude (H_ref) so that pressure tendencies reflect
atmospheric change rather than elevation change.

LCL estimation (cloud base height above ground) uses the common approximation:
    LCL_height (m above sensor) ≈ 125 * (T - Td), with T, Td in °C.
Then absolute LCL altitude (m AMSL) = H + 125 * (T - Td).

References (Wikipedia summaries for formulas and constants):
  - https://chatgpt.com/share/689a10b6-52d0-800a-b2f2-051a5ccb91cc
  - Barometric formula (troposphere, 0–11 km): https://en.wikipedia.org/wiki/Barometric_formula
  - International Standard Atmosphere constants: https://en.wikipedia.org/wiki/International_Standard_Atmosphere
  - Lifting Condensation Level approximation: https://en.wikipedia.org/wiki/Lifting_condensation_level

Notes:
  * Units: Pressures are handled in hPa for I/O, but formula uses Pa internally.
  * This module is intentionally lightweight and has no external dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import math
import time

# ---- Physical constants (SI) ----
T0_K = 288.15          # K, sea-level standard temperature
L0_K_per_m = -0.0065   # K/m, lapse rate in troposphere (negative)
g_m_s2 = 9.80665       # m/s^2
M0_kg_per_mol = 0.0289644  # kg/mol
R_J_per_molK = 8.3144598   # J/(mol·K)

# Unit helpers
HPA_TO_PA = 100.0
PA_TO_HPA = 1.0 / HPA_TO_PA

def pressure_at_altitude_pa(P0_pa: float, H_m: float) -> float:
    """
    Compute static pressure P(H) [Pa] at altitude H [m] given sea-level pressure P0 [Pa]
    using the tropospheric barometric formula provided by the user:
        P(H) = P0 * [ T0 / (T0 + L0*H) ]^( (g*M0) / (R*L0) )

    Constants (SI):
        T0_K = 288.15 K
        L0_K_per_m = -0.0065 K/m  (troposphere)
        g_m_s2 = 9.80665 m/s^2
        M0_kg_per_mol = 0.0289644 kg/mol
        R_J_per_molK = 8.3144598 J/(mol·K)

    Returns:
        Pressure at altitude H in Pa.
    """
    denom = T0_K + L0_K_per_m * H_m
    if denom <= 0:
        # Outside model validity, clamp to small positive number
        denom = 1e-6
    exponent = (g_m_s2 * M0_kg_per_mol) / (R_J_per_molK * L0_K_per_m)
    return P0_pa * (T0_K / denom) ** exponent

def adjust_pressure_to_reference_hpa(P_meas_hpa: float, H_meas_m: float, H_ref_m: float) -> float:
    """
    Adjust a measured pressure (at H_meas) to an equivalent pressure at a fixed reference altitude H_ref.
    We use the ratio form implied by the barometric formula:

        P_ref = P_meas * [ (T0) / (T0 + L0*(H_ref - H_meas)) ]^( (g*M0)/(R*L0) )

    This effectively "moves" the measured pressure to the reference altitude,
    removing the effect of elevation change so tendencies reflect atmospheric change.

    Args:
        P_meas_hpa : measured pressure at H_meas [hPa]
        H_meas_m   : measurement altitude [m]
        H_ref_m    : reference altitude [m]

    Returns:
        P_ref_hpa  : pressure equivalent at H_ref [hPa]
    """
    deltaH = H_ref_m - H_meas_m
    denom = T0_K + L0_K_per_m * deltaH
    if denom <= 0:
        denom = 1e-6
    exponent = (g_m_s2 * M0_kg_per_mol) / (R_J_per_molK * L0_K_per_m)
    P_meas_pa = P_meas_hpa * HPA_TO_PA
    P_ref_pa = P_meas_pa * (T0_K / denom) ** exponent
    return P_ref_pa * PA_TO_HPA

def lcl_above_sensor_m(T_C: float, Td_C: float) -> float:
    """
    Estimate LCL height above the sensor [m] using the approximation:
        LCL (m AGL) ≈ 125 * (T - Td), T, Td in °C.
    Returns max(0, value) to avoid negatives from noisy inputs.
    """
    return max(0.0, 125.0 * (T_C - Td_C))

@dataclass
class Sample:
    t_s: float           # Unix timestamp seconds
    T_C: float
    Td_C: float
    RH_pct: float
    H_m: float
    P_hpa: float
    LCL_meas_mAMSL: Optional[float] = None

@dataclass
class EngineConfig:
    trend_window_s: int = 3 * 3600  # 3 hours for tendencies
    # Rule thresholds (can be tuned):
    rapid_fall_hpa_per_h: float = 2.0     # NWS "falling rapidly" ~2 hPa/h
    three_hour_drop_hpa: float = 3.0      # ~3 hPa / 3h minimal deterioration flag
    dewpoint_depression_close_C: float = 3.0  # near saturation if Δ <= 2–3 °C
    td_rise_C_over_3h: float = 1.0        # moisture loading threshold
    lcl_low_above_m: float = 500.0        # cloud base within 0.5 km above you
    lcl_far_above_m: float = 1500.0       # fair bias if >1.5 km above you

@dataclass
class RuleResult:
    verdict: str                   # "Better", "Stable", "Worse"
    eta_hours: Tuple[int, int]     # (lower_bound_hours, upper_bound_hours)
    details: dict = field(default_factory=dict)

class NowcastEngine:
    def __init__(self, H_ref_m: Optional[float] = None, config: EngineConfig = EngineConfig()):
        """
        Initialize the engine.

        Args:
            H_ref_m: Optional fixed reference altitude for pressure adjustment.
                     If None, the first sample's altitude becomes the reference.
            config:  EngineConfig thresholds and window.
        """
        self.config = config
        self.samples: List[Sample] = []
        self.H_ref_m = H_ref_m

    def add_sample(self,
                   T_C: float,
                   Td_C: float,
                   RH_pct: float,
                   H_m: float,
                   P_hpa: float,
                   LCL_meas_mAMSL: Optional[float] = None,
                   t_s: Optional[float] = None):
        """Add a new observation sample."""
        if t_s is None:
            t_s = time.time()
        if self.H_ref_m is None:
            self.H_ref_m = H_m
        self.samples.append(Sample(t_s, T_C, Td_C, RH_pct, H_m, P_hpa, LCL_meas_mAMSL))
        # drop old samples outside the trend window
        t_cut = t_s - self.config.trend_window_s
        self.samples = [s for s in self.samples if s.t_s >= t_cut]

    def _trend(self) -> dict:
        """Compute trends over the stored window (using first vs last sample)."""
        if len(self.samples) < 2:
            return {"hours": 0.0}

        s0 = self.samples[0]
        s1 = self.samples[-1]
        dt_h = max(1e-6, (s1.t_s - s0.t_s) / 3600.0)

        # Adjust both pressures to the same reference altitude
        Pref0 = adjust_pressure_to_reference_hpa(s0.P_hpa, s0.H_m, self.H_ref_m)
        Pref1 = adjust_pressure_to_reference_hpa(s1.P_hpa, s1.H_m, self.H_ref_m)

        dP_hpa = Pref1 - Pref0
        dP_hpa_per_h = dP_hpa / dt_h

        # Dew point depression Δ = T - Td
        delta0 = s0.T_C - s0.Td_C
        delta1 = s1.T_C - s1.Td_C
        dDelta_C = (delta1 - delta0) / dt_h  # change per hour
        # Td trend
        dTd_C = (s1.Td_C - s0.Td_C) / dt_h

        # LCL estimates
        lcl0_above = lcl_above_sensor_m(s0.T_C, s0.Td_C)
        lcl1_above = lcl_above_sensor_m(s1.T_C, s1.Td_C)
        lcl0_amsl = s0.H_m + lcl0_above
        lcl1_amsl = s1.H_m + lcl1_above
        dLCL_m_per_h = (lcl1_amsl - lcl0_amsl) / dt_h

        return dict(
            hours=dt_h,
            P_ref0_hpa=Pref0,
            P_ref1_hpa=Pref1,
            dP_hpa=dP_hpa,
            dP_hpa_per_h=dP_hpa_per_h,
            delta0_C=delta0,
            delta1_C=delta1,
            dDelta_C_per_h=dDelta_C,
            dTd_C_per_h=dTd_C,
            LCL0_mAMSL=lcl0_amsl,
            LCL1_mAMSL=lcl1_amsl,
            dLCL_m_per_h=dLCL_m_per_h
        )

    def evaluate(self) -> RuleResult:
        """
        Evaluate rules and return a verdict with ETA and details.

        Verdict & ETA logic (simple, conservative mapping):
          - Strong WORSENING: P falling rapidly (<= -2 hPa/h) OR drop >= 3 hPa in 3h,
            combined with near-saturation (Δ <= 3°C) or Td rising ⇒ ETA 1–6 h.
          - Mild WORSENING: P falling but slower, OR Δ trending down ⇒ ETA 3–12 h.
          - Stabilizing: P steady/rising AND Δ increasing AND LCL rising/far ⇒ ETA 3–12 h toward "Better".
          - Otherwise STABLE: ETA 6–12 h.

        Also reports LCL_est vs LCL_meas (if available) on the latest sample.
        """
        cfg = self.config
        if not self.samples:
            return RuleResult("Stable", (6, 12), details={"note": "No samples yet."})

        trends = self._trend()
        details = {"trends": trends}

        # Latest sample
        s = self.samples[-1]
        delta_C = s.T_C - s.Td_C
        lcl_est_above = lcl_above_sensor_m(s.T_C, s.Td_C)
        lcl_est_amsl = s.H_m + lcl_est_above

        # LCL comparison (if measured given)
        lcl_meas_amsl = s.LCL_meas_mAMSL
        if lcl_meas_amsl is not None:
            lcl_err_m = lcl_est_amsl - lcl_meas_amsl
        else:
            lcl_err_m = None

        details["LCL"] = {
            "estimated_mAMSL": lcl_est_amsl,
            "estimated_above_sensor_m": lcl_est_above,
            "measured_mAMSL": lcl_meas_amsl,
            "estimate_minus_measured_m": lcl_err_m
        }

        # Rule flags
        rapid_fall = trends.get("dP_hpa_per_h", 0.0) <= -cfg.rapid_fall_hpa_per_h
        three_hr_drop = trends.get("dP_hpa", 0.0) <= -cfg.three_hour_drop_hpa and trends.get("hours", 0.0) >= 2.0
        near_sat = delta_C <= cfg.dewpoint_depression_close_C
        td_rising = trends.get("dTd_C_per_h", 0.0) >= (cfg.td_rise_C_over_3h / 3.0)  # per-hour equivalent
        delta_decreasing = trends.get("dDelta_C_per_h", 0.0) < 0.0
        lcl_low_now = lcl_est_above <= cfg.lcl_low_above_m
        lcl_rising_far = (trends.get("dLCL_m_per_h", 0.0) > 0.0) and (lcl_est_above >= cfg.lcl_far_above_m)

        # Decision logic
        # Strong worsening
        if (rapid_fall or three_hr_drop) and (near_sat or td_rising or lcl_low_now):
            verdict = "Worse"
            eta = (1, 6)
        # Moderate worsening
        elif (rapid_fall or three_hr_drop) or (delta_decreasing and td_rising):
            verdict = "Worse"
            eta = (3, 12)
        # Improving
        elif (trends.get("dP_hpa_per_h", 0.0) >= 0.2) and (trends.get("dDelta_C_per_h", 0.0) > 0.0) and lcl_rising_far:
            verdict = "Better"
            eta = (3, 12)
        else:
            verdict = "Stable"
            eta = (6, 12)

        details["rule_flags"] = dict(
            rapid_fall=rapid_fall,
            three_hr_drop=three_hr_drop,
            near_sat=near_sat,
            td_rising=td_rising,
            delta_decreasing=delta_decreasing,
            lcl_low_now=lcl_low_now,
            lcl_rising_far=lcl_rising_far
        )
        details["current"] = dict(
            T_C=s.T_C, Td_C=s.Td_C, RH_pct=s.RH_pct, H_m=s.H_m, P_hpa=s.P_hpa,
            P_ref_hpa=adjust_pressure_to_reference_hpa(s.P_hpa, s.H_m, self.H_ref_m),
            dewpoint_depression_C=delta_C
        )

        return RuleResult(verdict, eta, details)

# ---- Minimal demo when run as a script ----
if __name__ == "__main__":
    eng = NowcastEngine(H_ref_m=None)
    # Example: add two samples ~3h apart with falling pressure and moisture loading
    t0 = time.time()
    eng.add_sample(T_C=12.0, Td_C=7.0, RH_pct=70.0, H_m=2000.0, P_hpa=780.0, t_s=t0)
    eng.add_sample(T_C=11.0, Td_C=9.5, RH_pct=80.0, H_m=2300.0, P_hpa=755.0, t_s=t0 + 3*3600)

    res = eng.evaluate()
    print("Verdict:", res.verdict, "\n")
    print("ETA (hours):", res.eta_hours, "\n")
    print("Details:", res.details, "\n")
