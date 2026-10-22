"""
engine.py — SupplyChain-Sensi analytics core.

Pure-Python (stdlib only), UI-agnostic. app.py imports exactly one symbol:
    calculate_enterprise_analytics(...)

Units
-----
temp            : °C
humidity        : % relative humidity (0-100)
moisture        : % grain kernel moisture content, wet basis
days            : days already in storage
batch_size      : metric tonnes
market_price    : ₹ per quintal (1 quintal = 100 kg → 10 quintals per tonne)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

# ─────────────────────────────── Threat palette ────────────────────────────────
NEON_RED = "#FF1744"
CYBER_AMBER = "#FFB000"
MATRIX_GREEN = "#00FF41"

# ───────────────────────── Per-crop threshold configuration ────────────────────
# temp_safe / temp_critical : °C band where metabolic + insect activity ramps up
# humidity_threshold        : % RH above which moulds / aflatoxin risk climbs
# moisture_safe/critical    : % kernel moisture for safe vs. high-risk storage
# max_days                  : nominal safe storage lifecycle under ideal conditions
GRAIN_CONFIG: Dict[str, Dict[str, float]] = {
    "Wheat": {
        "temp_safe": 20.0, "temp_critical": 35.0,
        "humidity_threshold": 65.0,
        "moisture_safe": 12.0, "moisture_critical": 14.0,
        "max_days": 270,
    },
    "Rice (Paddy)": {
        "temp_safe": 22.0, "temp_critical": 36.0,
        "humidity_threshold": 70.0,
        "moisture_safe": 13.0, "moisture_critical": 15.0,
        "max_days": 240,
    },
    "Maize (Corn)": {
        "temp_safe": 18.0, "temp_critical": 32.0,
        "humidity_threshold": 65.0,
        "moisture_safe": 13.0, "moisture_critical": 15.5,
        "max_days": 180,
    },
    "Pulses / Lentils": {
        "temp_safe": 22.0, "temp_critical": 34.0,
        "humidity_threshold": 60.0,
        "moisture_safe": 10.0, "moisture_critical": 12.0,
        "max_days": 210,
    },
}

# ─────────────────────────────── Model constants ───────────────────────────────
VENTILATION_STRESS_REDUCTION = 0.35   # spec: -35 % cumulative stress when active
DAMAGE_CURVE_K = 0.45                 # saturating damage curve steepness
CRITICAL_STRESS, ELEVATED_STRESS = 75.0, 30.0   # tier cut-offs (stress index)
CRITICAL_RATE, ELEVATED_RATE = 6.0, 2.0         # tier cut-offs (effective multiplier)

# Carbon model (documented assumptions, tune per facility)
GRID_KG_CO2_PER_KWH = 0.82            # India grid average, approx.
BASE_KG_CO2_PER_TONNE_DAY = 0.012     # handling, lighting, telemetry
FAN_KWH_PER_TONNE_DAY = 0.35          # exhaust array draw at ~50 % duty cycle
EMBODIED_KG_CO2_PER_KG_GRAIN = 0.6    # footprint wasted when grain spoils


def _validate(grain_type: str, temp: float, humidity: float, moisture: float,
              days: float, batch_size: float, market_price: float) -> None:
    if grain_type not in GRAIN_CONFIG:
        raise ValueError(f"Unknown grain_type '{grain_type}'. "
                         f"Valid: {', '.join(GRAIN_CONFIG)}")
    if not 0 <= humidity <= 100:
        raise ValueError("humidity must be within 0-100 %.")
    if moisture <= 0 or moisture >= 100:
        raise ValueError("moisture must be within (0, 100) %.")
    if days < 0 or batch_size < 0 or market_price < 0:
        raise ValueError("days, batch_size and market_price must be non-negative.")


def _remediation(cfg: Dict[str, float], tier: str, temp: float, humidity: float,
                 moisture: float, ventilation_status: bool) -> List[str]:
    """Build targeted, condition-specific remediation bullets."""
    steps: List[str] = []
    if temp > cfg["temp_safe"]:
        steps.append(
            f"THERMAL: Vault at {temp:.1f}°C exceeds the {cfg['temp_safe']:.0f}°C safe band. "
            "Run aeration at night/early morning, and check for hot spots with probe "
            "thermometers on a 3 m grid.")
    if humidity > cfg["humidity_threshold"]:
        steps.append(
            f"HUMIDITY: RH {humidity:.0f}% is above the {cfg['humidity_threshold']:.0f}% "
            "threshold. Seal ingress points, deploy desiccant or dehumidification, "
            "and keep intake doors closed during peak humidity hours.")
    if moisture > cfg["moisture_safe"]:
        steps.append(
            f"MOISTURE: Kernel moisture {moisture:.1f}% exceeds {cfg['moisture_safe']:.0f}%. "
            "Re-dry the lot to the safe level and turn the grain to break up wet pockets.")
    if not ventilation_status and tier != "NOMINAL STATE":
        steps.append(
            "VENTILATION: Exhaust arrays are OFF. Engage them now; this cuts the "
            "cumulative stress index by 35%.")

    if tier == "CRITICAL THREAT":
        steps += [
            "ESCALATE: Notify the facility head and QA team immediately and quarantine the batch.",
            "SAMPLING: Pull multi-depth samples for aflatoxin, insect and fungal counts within 24 h.",
            "LIQUIDATION: Evaluate priority dispatch or forward sale to cap further capital loss.",
            "FUMIGATION: If infestation is confirmed, run a licensed phosphine fumigation cycle.",
        ]
    elif tier == "ELEVATED RISK":
        steps += [
            "MONITOR: Increase sensor polling to hourly and review trends every shift.",
            "ROTATION: Schedule FIFO rotation of the most affected stacks within 7 days.",
        ]
    else:
        steps.append("MAINTAIN: Conditions are nominal. Continue routine inspection and logging.")
    return steps


def calculate_enterprise_analytics(
    grain_type: str,
    temp: float,
    humidity: float,
    moisture: float,
    days: float,
    batch_size: float,
    market_price: float,
    ventilation_status: bool,
) -> Dict[str, Any]:
    """Run the biochemical + financial simulation and return a flat result dict."""
    _validate(grain_type, temp, humidity, moisture, days, batch_size, market_price)
    cfg = GRAIN_CONFIG[grain_type]

    # ── 1. Nonlinear environmental multipliers (each ≥ 1.0) ──
    t_range = cfg["temp_critical"] - cfg["temp_safe"]
    t_ex = max(0.0, temp - cfg["temp_safe"]) / t_range
    temp_mult = 1.0 + 1.8 * t_ex ** 1.6                     # power-law thermal ramp

    h_span = 100.0 - cfg["humidity_threshold"]
    h_ex = max(0.0, humidity - cfg["humidity_threshold"]) / h_span
    humidity_mult = math.exp(3.2 * h_ex)                    # exponential past threshold

    m_ex = max(0.0, moisture - cfg["moisture_safe"]) / cfg["moisture_safe"]
    moisture_mult = 1.0 + 6.0 * m_ex ** 1.3                 # steep kernel-moisture penalty
    if moisture >= cfg["moisture_critical"]:                # hard-limit breach surcharge
        moisture_mult *= 1.0 + 0.5 * (moisture - cfg["moisture_critical"] + 1)

    kinetic_multiplier = temp_mult * humidity_mult * moisture_mult

    # ── 2. Cumulative stress index (100 = nominal lifecycle fully consumed) ──
    ventilation_factor = 1.0 - VENTILATION_STRESS_REDUCTION if ventilation_status else 1.0
    base_rate = 100.0 / cfg["max_days"]                     # index points / day at 1.0×
    stress_rate = base_rate * kinetic_multiplier * ventilation_factor
    stress_index = stress_rate * days
    effective_multiplier = kinetic_multiplier * ventilation_factor

    # ── 3. Volumetric damage (saturating curve) and safe-days projection ──
    x = stress_index / 100.0
    damage_pct = 100.0 * (1.0 - math.exp(-DAMAGE_CURVE_K * x))
    safe_days = max(0.0, (100.0 - stress_index) / stress_rate) if stress_rate > 0 else 0.0

    # ── 4. Financial model ──
    valuation = batch_size * 10.0 * market_price            # tonnes → quintals
    loss_exposure = valuation * damage_pct / 100.0
    d_damage_d_index = DAMAGE_CURVE_K * math.exp(-DAMAGE_CURVE_K * x)   # %-points per index pt
    loss_velocity = valuation / 100.0 * d_damage_d_index * stress_rate  # ₹/day, instantaneous
    residual_value = valuation - loss_exposure

    # ── 5. Carbon footprint index (kg CO₂e) ──
    base_kg = BASE_KG_CO2_PER_TONNE_DAY * batch_size * days
    fan_kwh = FAN_KWH_PER_TONNE_DAY * batch_size * days if ventilation_status else 0.0
    fan_kg = fan_kwh * GRID_KG_CO2_PER_KWH
    spoilage_kg = batch_size * 1000.0 * damage_pct / 100.0 * EMBODIED_KG_CO2_PER_KG_GRAIN
    carbon_total = base_kg + fan_kg + spoilage_kg

    # ── 6. Threat tier ──
    if stress_index >= CRITICAL_STRESS or effective_multiplier >= CRITICAL_RATE:
        tier, color, code = "CRITICAL THREAT", NEON_RED, "STATUS_CRITICAL_300"
    elif stress_index >= ELEVATED_STRESS or effective_multiplier >= ELEVATED_RATE:
        tier, color, code = "ELEVATED RISK", CYBER_AMBER, "STATUS_ELEVATED_200"
    else:
        tier, color, code = "NOMINAL STATE", MATRIX_GREEN, "STATUS_NOMINAL_100"

    return {
        "grain_type": grain_type,
        "threat_tier": tier,
        "threat_color": color,
        "status_code": code,
        "ventilation_active": bool(ventilation_status),
        # stress / kinetics
        "temp_multiplier": round(temp_mult, 3),
        "humidity_multiplier": round(humidity_mult, 3),
        "moisture_multiplier": round(moisture_mult, 3),
        "kinetic_multiplier": round(kinetic_multiplier, 3),
        "effective_multiplier": round(effective_multiplier, 3),
        "stress_index": round(stress_index, 2),
        "volumetric_damage_pct": round(damage_pct, 2),
        "safe_days_remaining": round(safe_days, 1),
        "max_storage_days": int(cfg["max_days"]),
        # financial (₹)
        "total_valuation_inr": round(valuation, 2),
        "loss_exposure_inr": round(loss_exposure, 2),
        "residual_value_inr": round(residual_value, 2),
        "loss_velocity_inr_per_day": round(loss_velocity, 2),
        # carbon (kg CO₂e)
        "carbon_operational_kg": round(base_kg, 2),
        "carbon_ventilation_kg": round(fan_kg, 2),
        "carbon_spoilage_kg": round(spoilage_kg, 2),
        "carbon_footprint_index_kg": round(carbon_total, 2),
        "carbon_intensity_kg_per_tonne": round(carbon_total / batch_size, 3) if batch_size else 0.0,
        # actions
        "remediation": _remediation(cfg, tier, temp, humidity, moisture, bool(ventilation_status)),
    }


if __name__ == "__main__":  # quick smoke test
    import json
    print(json.dumps(calculate_enterprise_analytics(
        "Wheat", 30, 80, 14.5, 90, 500, 2400, False), indent=2, ensure_ascii=False))
