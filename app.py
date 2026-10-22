"""
app.py — SupplyChain-Sensi // Enterprise Control Center (Streamlit frontend).

All calculations live in engine.py; this file only renders.
Run:  streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from engine import GRAIN_CONFIG, calculate_enterprise_analytics

# ───────────────────────────── Page configuration ──────────────────────────────
st.set_page_config(page_title="SupplyChain-Sensi | Control Center",
                   page_icon="🛰️", layout="wide")

# ───────────────────────────────── Styling ─────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

:root { --ink:#E2E8F0; --muted:#8B9BB4; --glass:rgba(15,23,42,.55); --edge:rgba(148,163,184,.18); }

.stApp {
  background: linear-gradient(180deg, #060B19 0%, #02040A 100%);
  color: var(--ink);
  font-family: 'Chakra Petch', 'Segoe UI', sans-serif;
}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div[data-testid="stMarkdownContainer"] { color: var(--ink); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1500px; }

/* Sidebar: dark glass */
section[data-testid="stSidebar"] {
  background: rgba(6,11,25,.78);
  backdrop-filter: blur(14px);
  border-right: 1px solid var(--edge);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
.side-title {
  font-weight: 700; font-size: 1.05rem; letter-spacing: .04em;
  padding-bottom: .5rem; margin: 1rem 0 .6rem;
  border-bottom: 2px solid transparent;
  border-image: linear-gradient(90deg, #22D3EE, transparent) 1;
}

/* Header banner */
.hero {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  padding: 1.1rem 1.6rem; margin-bottom: 1.2rem; border-radius: 16px;
  background: var(--glass); backdrop-filter: blur(12px);
  border: 1px solid var(--edge);
  box-shadow: inset 0 0 40px rgba(34,211,238,.06), 0 8px 30px rgba(0,0,0,.45);
}
.hero h1 { margin: 0; font-size: 1.55rem; font-weight: 700; letter-spacing: .02em; color: #F1F5F9; }
.live { display: flex; align-items: center; gap: .6rem; font-family: 'IBM Plex Mono', monospace; font-size: .85rem; color: var(--muted); }
.dot { width: 11px; height: 11px; border-radius: 50%; background: #00FF41;
       box-shadow: 0 0 10px #00FF41, 0 0 22px #00FF41; animation: pulse 1.8s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .45; transform: scale(.8); } }

/* Telemetry cards */
.card-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; margin-bottom: 1.4rem; }
@media (max-width: 1100px) { .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px)  { .card-grid { grid-template-columns: 1fr; } }
.card {
  display: flex; flex-direction: column; justify-content: space-between; gap: .5rem;
  padding: 1.15rem 1.3rem; border-radius: 16px; min-height: 140px;
  background: var(--glass); backdrop-filter: blur(12px);
  border: 1px solid var(--accent); 
  box-shadow: inset 0 0 28px color-mix(in srgb, var(--accent) 18%, transparent),
              0 0 18px color-mix(in srgb, var(--accent) 28%, transparent);
  transition: 0.3s;
}
.card:hover { transform: translateY(-3px); }
.card .label { font-size: .85rem; color: var(--muted); }
.card .value { font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 1.7rem; color: var(--accent);
               text-shadow: 0 0 14px color-mix(in srgb, var(--accent) 55%, transparent); overflow-wrap: anywhere; }
.card .sub { font-size: .78rem; color: var(--muted); font-family: 'IBM Plex Mono', monospace; }

/* Panels */
.panel-title { font-weight: 700; font-size: 1.1rem; margin-bottom: .6rem; color: #F1F5F9; }
.glass-panel { padding: 1rem 1.2rem; border-radius: 14px; background: var(--glass);
               backdrop-filter: blur(12px); border: 1px solid var(--edge); }
.metric-row { display: flex; justify-content: space-between; gap: 1rem; padding: .55rem 0;
              border-bottom: 1px solid var(--edge); font-size: .92rem; }
.metric-row:last-child { border-bottom: none; }
.metric-row b { font-family: 'IBM Plex Mono', monospace; font-weight: 600; text-align: right; }

/* Command-style download button */
.stDownloadButton button {
  width: 100%; border-radius: 10px; font-weight: 700; letter-spacing: .03em;
  color: #02040A !important; border: none;
  background: linear-gradient(90deg, #22D3EE, #6366F1);
  box-shadow: 0 0 18px rgba(34,211,238,.35); transition: 0.3s;
}
.stDownloadButton button:hover { transform: translateY(-3px); box-shadow: 0 0 26px rgba(99,102,241,.55); }
.stDownloadButton button p { color: #02040A !important; }

/* Tabs */
button[data-baseweb="tab"] { color: var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { color: #22D3EE; }

@media (prefers-reduced-motion: reduce) { .dot { animation: none; } .card, .stDownloadButton button { transition: none; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)  # NB: the real kwarg is unsafe_allow_html


def html(markup: str) -> None:
    """Render HTML; strip per-line indentation so Markdown never treats it as a code block."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def inr(value: float) -> str:
    """Format a number in Indian digit grouping (e.g. 12,34,567)."""
    n, neg = int(round(abs(value))), value < 0
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{'-' if neg else ''}₹{s}"


# ─────────────────────────── Sidebar: telemetry panel ──────────────────────────
with st.sidebar:
    html('<div class="side-title">🌾 Asset selection</div>')
    grain = st.selectbox("Grain type", list(GRAIN_CONFIG.keys()))
    batch_size = st.number_input("Batch mass (metric tonnes)", min_value=1.0, value=500.0, step=10.0)
    price = st.number_input("Market price (₹ per quintal)", min_value=0.0, value=2400.0, step=50.0)

    html('<div class="side-title">⚙️ Active controls</div>')
    ventilation = st.toggle("Auxiliary Exhaust Ventilation Arrays", value=False,
                            help="Reduces the cumulative stress index by 35%.")

    html('<div class="side-title">📡 Sensor arrays</div>')
    temp = st.slider("Ambient vault temperature (°C)", 0.0, 60.0, 28.0, 0.1)
    humidity = st.slider("Structural relative humidity (%)", 10.0, 100.0, 70.0, 0.5)
    moisture = st.slider("Kernel internal moisture (%)", 5.0, 30.0, 13.0, 0.1)
    days = st.slider("Storage runtime (days)", 0, 365, 60, 1)

# ──────────────────────────────── Engine call ──────────────────────────────────
r = calculate_enterprise_analytics(grain, temp, humidity, moisture, days,
                                   batch_size, price, ventilation)
accent = r["threat_color"]
now = datetime.now().strftime("%d %b %Y, %H:%M:%S")

# ─────────────────────────────── 1. Header banner ──────────────────────────────
html(f"""
<div class="hero">
  <h1>🛰️ SupplyChain-Sensi // Enterprise Control Center</h1>
  <div class="live"><span class="dot"></span>LIVE · uplink stable · {now}</div>
</div>
""")

# ──────────────────────────── 2. Main analytics row ────────────────────────────
def card(label: str, value: str, sub: str) -> str:
    return (f'<div class="card" style="--accent:{accent}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub">{sub}</div></div>')


html('<div class="card-grid">'
     + card("Current threat matrix", r["threat_tier"], r["status_code"])
     + card("Est. safe days remaining", f'{r["safe_days_remaining"]:,.1f} d',
            f'nominal lifecycle {r["max_storage_days"]} d')
     + card("Active capital loss exposure", inr(r["loss_exposure_inr"]),
            f'of {inr(r["total_valuation_inr"])} batch value')
     + card("System loss velocity", f'{inr(r["loss_velocity_inr_per_day"])}/day',
            f'stress index {r["stress_index"]:.1f}')
     + '</div>')

# ────────────────────────── 3. Comparative operational grid ────────────────────
left, right = st.columns(2)

with left:
    html('<div class="panel-title">🚨 Remediation Action Deck</div>')
    bullets = "\n".join(f"- {step}" for step in r["remediation"])
    if r["threat_tier"] == "CRITICAL THREAT":
        st.error(bullets)
    elif r["threat_tier"] == "ELEVATED RISK":
        st.warning(bullets)
    else:
        st.success(bullets)

    export = pd.DataFrame([{k: (" | ".join(v) if isinstance(v, list) else v) for k, v in r.items()}])
    st.download_button("⬇ EXPORT TELEMETRY REPORT (.csv)",
                       data=export.to_csv(index=False).encode("utf-8"),
                       file_name=f"sensi_report_{datetime.now():%Y%m%d_%H%M%S}.csv",
                       mime="text/csv")

with right:
    html('<div class="panel-title">🧬 Biochemical Stress Analysis</div>')
    tab_kin, tab_fin, tab_carbon = st.tabs(["Kinetics", "Financial", "Carbon"])

    def rows(items) -> None:
        html('<div class="glass-panel">'
             + "".join(f'<div class="metric-row"><span>{k}</span><b>{v}</b></div>' for k, v in items)
             + '</div>')

    with tab_kin:
        rows([
            ("Thermal multiplier", f'{r["temp_multiplier"]:.3f}×'),
            ("Humidity multiplier", f'{r["humidity_multiplier"]:.3f}×'),
            ("Moisture multiplier", f'{r["moisture_multiplier"]:.3f}×'),
            ("Kinetic decay multiplier", f'{r["kinetic_multiplier"]:.3f}×'),
            ("Effective multiplier (after ventilation)", f'{r["effective_multiplier"]:.3f}×'),
            ("Cumulative stress index", f'{r["stress_index"]:.2f}'),
            ("Volumetric damage", f'{r["volumetric_damage_pct"]:.2f}%'),
        ])
        st.progress(min(r["volumetric_damage_pct"] / 100.0, 1.0))
    with tab_fin:
        rows([
            ("Total batch valuation", inr(r["total_valuation_inr"])),
            ("Capital degradation", inr(r["loss_exposure_inr"])),
            ("Residual value", inr(r["residual_value_inr"])),
            ("Loss velocity", f'{inr(r["loss_velocity_inr_per_day"])}/day'),
        ])
    with tab_carbon:
        rows([
            ("Operational", f'{r["carbon_operational_kg"]:,.2f} kg CO₂e'),
            ("Ventilation arrays", f'{r["carbon_ventilation_kg"]:,.2f} kg CO₂e'),
            ("Spoilage (embodied)", f'{r["carbon_spoilage_kg"]:,.2f} kg CO₂e'),
            ("Carbon footprint index", f'{r["carbon_footprint_index_kg"]:,.2f} kg CO₂e'),
            ("Intensity", f'{r["carbon_intensity_kg_per_tonne"]:.3f} kg/tonne'),
        ])

# ───────────────────────────── 4. System heartbeat alert ───────────────────────
st.markdown("---")
heartbeat = f"[{now}] node-sensi-01 · {r['status_code']} · "
if r["status_code"] == "STATUS_CRITICAL_300":
    st.error(heartbeat + f"Critical degradation in {grain} lot. Loss exposure {inr(r['loss_exposure_inr'])}. Escalate now.")
elif r["status_code"] == "STATUS_ELEVATED_200":
    st.warning(heartbeat + f"Stress rising in {grain} lot. About {r['safe_days_remaining']:.0f} safe days remain.")
else:
    st.success(heartbeat + f"All sensor channels nominal for {grain}. No action required.")
