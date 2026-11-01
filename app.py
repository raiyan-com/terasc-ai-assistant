"""
Standalone demo site for the TER-ASC AI Assistant.

The sidebar stands in for the real TER-ASC app: there, these values come from the
user's inputs and the prediction model. Run with:  streamlit run app.py
"""

import streamlit as st

from terasc_chat import heat_level, render_chat

st.set_page_config(page_title="TER-ASC AI Assistant", page_icon="🤖", layout="wide")

# Same look as the TER-ASC app.
st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(145deg,#0f2027 0%,#203a43 50%,#2c5364 100%);}
    [data-testid="stSidebar"] {background: linear-gradient(195deg,#1a2f3f 0%,#1e3a4a 100%);
        border-right: 1px solid rgba(255,255,255,0.1);}
    .main-header {font-size: 1.9rem; font-weight: 700; text-align: center; color: white;
        padding: 1.2rem; background: rgba(255,255,255,0.08); backdrop-filter: blur(12px);
        border-radius: 20px; margin-bottom: 1.5rem; border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);}
    @media (max-width: 768px) {.main-header {font-size: 1.5rem; padding: .8rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ⚙️ Site conditions")
    st.caption("Demo values. In TER-ASC these come from the sidebar and the model automatically.")
    temp = st.number_input("Temp (°C)", 20.0, 50.0, 34.0, 0.1)
    humidity = st.number_input("Humidity (%)", 0.0, 100.0, 65.0, 1.0)
    wind = st.number_input("Wind Speed (m/s)", 0.0, 10.0, 1.5, 0.1)
    clo = st.slider("Clothing insulation (clo)", 0.36, 1.0, 0.57, 0.01)
    met = st.slider("Metabolic rate (met)", 2.1, 4.0, 3.2, 0.1)
    work_type = st.selectbox(
        "Work type", ["Rest (R)", "Light (LW)", "Moderate (MW)", "Heavy (HW)", "Very Heavy (VHW)"], index=3
    )
    height = st.slider("Working height (m)", 0, 100, 0)

    st.markdown("### 📊 Predicted outputs")
    c1, c2 = st.columns(2)
    pet = c1.number_input("PET (°C)", value=36.9, step=0.1)
    pmv = c2.number_input("PMV", value=2.76, step=0.01)
    ppd = c1.number_input("PPD (%)", value=88.4, step=0.1)
    set_ = c2.number_input("SET (°C)", value=35.7, step=0.1)
    rws = c1.number_input("RWS (m/s)", value=3.4, step=0.1)
    ce = c2.number_input("CE (°C)", value=12.9, step=0.1)

    share = st.toggle("Share these with the assistant", value=True)

st.markdown(
    '<div class="main-header">Thermal Exposure and Risk Analytics System in Construction (TER-ASC)</div>',
    unsafe_allow_html=True,
)

context = {
    "Air temperature (°C)": temp,
    "Relative humidity (%)": humidity,
    "Wind speed (m/s)": wind,
    "Clothing insulation (clo)": clo,
    "Metabolic rate (met)": met,
    "Work type": work_type,
    "Working height (m)": height,
    "PET (°C)": pet,
    "Heat risk level": heat_level(pet),
    "PMV": pmv,
    "PPD (%)": ppd,
    "SET (°C)": set_,
    "RWS (m/s)": rws,
    "CE (°C)": ce,
}

_, middle, _ = st.columns([1, 6, 1])
with middle:
    render_chat(context if share else None)
