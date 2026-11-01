"""
TER-ASC AI Assistant: a drop-in Streamlit chat for the TER-ASC heat-stress app.

Usage inside any Streamlit app:

    from terasc_chat import render_chat
    render_chat(context={"PET (°C)": 36.9, "PMV": 2.76, ...})  # context is optional

Needs a free Google Gemini API key in st.secrets["GEMINI_API_KEY"] or the
GEMINI_API_KEY environment variable (get one at https://aistudio.google.com/apikey).
"""

import os

import streamlit as st
from google import genai
from google.genai import errors, types

# Tried in order. Free-tier limits are per model, so when one runs out we move on.
MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
HISTORY_SENT = 12  # how many recent messages the model sees
MAX_QUESTIONS_PER_SESSION = 40  # protects the shared free quota on a public site

SUGGESTED_QUESTIONS = [  # (button label, question sent)
    ("What do my results mean?", "What do my current PET and PMV values mean?"),
    ("Work-rest schedule", "How long should my crew work before taking a break?"),
    ("PET vs SET", "What is the difference between PET and SET?"),
    ("Effect of height", "How does working height change heat stress?"),
]

PET_LEVELS = [  # (lower bound °C, label), as used by TER-ASC
    (41, "VERY HOT"),
    (35, "HOT"),
    (29, "WARM"),
    (23, "SLIGHTLY WARM"),
    (float("-inf"), "COMFORTABLE"),
]

SYSTEM_PROMPT = """
You are the AI assistant of TER-ASC (Thermal Exposure and Risk Analytics System in
Construction), a web app that predicts heat stress for outdoor construction workers.
You help safety engineers, site managers, workers and students understand the app's
results and act on them safely.

## About the app
- Developed by Md. Tushar Ali (PhD student), Department of Civil & Environmental
  Engineering, New Jersey Institute of Technology (NJIT), NJ, USA.
- Based on the Building and Environment article "Heat stress and thermal discomfort in
  construction: Implications for occupational safety and regulation"
  (https://www.sciencedirect.com/science/article/pii/S0360132326001769).
  Do not invent findings from this article; for details, point users to the link.
- Inputs (sidebar): air temperature 20-50 °C, relative humidity 0-100 %, wind speed
  0-10 m/s, clothing insulation 0.36-1.0 clo (default 0.57), metabolic rate 2.1-4.0 met
  (default 3.2 = Heavy work), working height 0-100 m, baseline productivity (units/hr,
  default 100), and the prediction model (Neural Network, AI-based ML). A
  "Show Model Performance" option shows how well the model fits.
- Outputs (ground level): PET, PMV, PPD, SET, RWS and CE, a thermal sensation scale,
  a work recommendation, and four tabs: PET Map (maximum PET distribution, April
  2021-2024), Vertical Analysis (PET and PMV versus working height 0-100 m),
  Productivity (loss by work type) and Safety Guide (personalised guidance for
  managers and for workers).

## Metrics
- PET, Physiological Equivalent Temperature (°C): the air temperature of a reference
  indoor setting at which the body's heat balance matches the actual outdoor
  conditions. TER-ASC uses it as the main heat-risk indicator.
- PMV, Predicted Mean Vote: average thermal sensation on the ISO 7730 scale
  (-3 cold, 0 neutral, +3 hot); TER-ASC can show values above 3 in extreme heat.
- PPD, Predicted Percentage Dissatisfied (%): share of people expected to feel
  uncomfortable, derived from PMV (minimum about 5 %).
- SET, Standard Effective Temperature (°C): temperature of a standard environment
  (50 % humidity, still air) that would give the same skin temperature and skin
  wetness as the actual conditions.
- RWS, Relative Wind Speed (m/s): air speed relative to the worker's body, predicted
  by the model.
- CE, Cooling Effect (°C): how much the air movement lowers SET compared with still air
  (ASHRAE 55 concept). Higher CE means wind is helping more.

## Thresholds used by TER-ASC
- PET: > 41 °C VERY HOT | 35-41 HOT | 29-35 WARM | 23-29 SLIGHTLY WARM | < 23 COMFORTABLE
- PMV: >= 3.0 extreme discomfort | 2.5-3.0 very | 2.0-2.5 moderate | 1.5-2.0 discomfort
  | 1.0-1.5 slight

## What the app recommends at each level
(Shown for heavy work; the app adapts it to the selected work type.)
- VERY HOT: "Extreme heat stress, unsafe for any physical work. Suspend all outdoor
  work." Productivity loss about 25-30 %. Managers: only emergency tasks in shaded
  areas; if critical, 15 min work / 45 min rest in air conditioning; oral rehydration
  (ORS) stations every 15 m; mandatory drinking every 15 min; ice-cooled water; AC rest
  areas; cooling vests for heavy work; medical team on site. Workers: light loose
  clothing, wide-brim hat, SPF 50+, 250 ml water every 15 min with ORS, no caffeine or
  alcohol, stop if unwell, stay in AC when not working, constant buddy checks. Warning
  signs: headache, dizziness, nausea, confusion, so seek help immediately.
- HOT: "High heat stress, significant strain. Limit work to 45 min sessions."
  Productivity loss about 15-25 %. Managers: 45 min work / 15 min rest; schedule heavy
  work before 10 AM; water stations every 25 m; 250 ml every 30 min; electrolytes for
  heavy work; shaded rest areas with fans, cooling towels and ice packs. Workers:
  breathable clothing, sun protection, SPF 30+, moderate pace, buddy system; watch for
  fatigue, cramps and headache and report symptoms.
- WARM: "Moderate heat stress, reduced work capacity. Normal work with breaks."
  Productivity loss about 5-15 %. Managers: 60 min work / 10 min rest for heavy work,
  normal hours, accessible water and hydration reminders, shaded rest areas. Workers:
  standard work clothes, regular water breaks, normal pace, breaks in shade, listen to
  your body and speak up about discomfort.
- SLIGHTLY WARM / COMFORTABLE: normal work, full schedule, standard breaks, normal water
  access, shade if needed. Little or no productivity loss.

## Productivity examples from the app (loss by work type)
- PET 36.9 °C: Rest 7.5 %, Light 7.4 %, Moderate 21.2 %, Heavy 24.3 %, Very Heavy 26.2 %.
- PET 50.0 °C: Rest 26.8 %, Light 28.3 %, Moderate 29.7 %, Heavy 29.9 %, Very Heavy 29.9 %.
- PET 27.7 °C: no loss. For other values, tell users to check the Productivity tab.

## Height
The Vertical Analysis tab shows PET and PMV from 0 to 100 m. In the app, PET usually
drops with height (for example, because wind is stronger higher up). Point users to
that tab for exact values at their working height.

## How to answer
- Be concise and practical: short paragraphs or bullet points, usually under 150
  words unless the user asks for more. Give °F in brackets when it helps.
- If current conditions are provided below, use them when the user says "my",
  "current", "now", "today" and so on, and quote the actual numbers.
- Stay on topic: heat stress, thermal comfort, construction safety and this app. For
  unrelated requests, say briefly that you can only help with TER-ASC topics.
- Never claim certainty you don't have. You are not a doctor: for suspected heat
  stroke (confusion, fainting, hot dry skin, seizures) tell the user to call 911 or
  local emergency services right away and start cooling the person. Remind users to
  also follow OSHA guidance and their employer's heat illness prevention plan.
- Answer in the language the user writes in.
""".strip()


def heat_level(pet):
    """TER-ASC heat-risk label for a PET value in °C."""
    return next(label for bound, label in PET_LEVELS if pet > bound)


class ChatError(Exception):
    """A problem we can explain to the user in plain words."""


def _api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # no secrets.toml at all
        key = None
    return key or os.environ.get("GEMINI_API_KEY")


@st.cache_resource(show_spinner=False)
def _client(api_key):
    return genai.Client(api_key=api_key)


def _fmt(value):
    return f"{value:.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def _system_prompt(context):
    if not context:
        return SYSTEM_PROMPT
    lines = "\n".join(f"- {name}: {_fmt(value)}" for name, value in context.items())
    return f"{SYSTEM_PROMPT}\n\n## Current conditions on the user's screen\n{lines}"


def _stream_reply(api_key, system, history):
    """Yield the answer text, trying each model in MODELS until one works."""
    history = history[-HISTORY_SENT:]
    while history and history[0]["role"] != "user":  # Gemini expects a user turn first
        history = history[1:]
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in history
    ]
    client = _client(api_key)
    last_error = None
    for model in MODELS:
        # Low thinking keeps replies fast; retry without it if a model rejects the setting.
        for thinking in (types.ThinkingConfig(thinking_level="low"), None):
            config = types.GenerateContentConfig(system_instruction=system, thinking_config=thinking)
            sent_text = False
            try:
                for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config):
                    if chunk.text:
                        sent_text = True
                        yield chunk.text
                return
            except errors.APIError as e:
                if sent_text:
                    raise ChatError("The answer was cut off. Please ask again.") from e
                last_error = e
                if e.code in (401, 403) or "API key" in str(e):
                    raise ChatError("The Gemini API key is missing or invalid. Check GEMINI_API_KEY.") from e
                if e.code == 400 and thinking is not None:
                    continue
                break  # quota, overload or unknown model: try the next model
    if last_error is not None and last_error.code == 429:
        raise ChatError("The free AI quota is used up for the moment. Please try again in a minute.")
    raise ChatError("The AI service is not responding right now. Please try again shortly.") from last_error


def _inject_style():
    st.markdown(
        """
        <style>
        [data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chat(context=None, key="terasc_chat", height=460, style=True):
    """Draw the assistant. `context` maps labels to current inputs/predictions."""
    if style:
        _inject_style()
    messages_key = f"{key}_messages"
    messages = st.session_state.setdefault(messages_key, [])

    title_col, clear_col = st.columns([5, 1], vertical_alignment="center")
    title_col.markdown("#### 🤖 TER-ASC AI Assistant")
    if messages and clear_col.button("Clear", key=f"{key}_clear", help="Clear the chat"):
        st.session_state[messages_key] = []
        st.rerun()

    api_key = _api_key()
    if not api_key:
        st.warning(
            "The assistant needs a free Google Gemini API key. Get one at "
            "https://aistudio.google.com/apikey and add it as `GEMINI_API_KEY` in Streamlit secrets."
        )
        return

    # Scrollable once there is a conversation; while empty it only takes the space it needs.
    box = st.container(height=height, border=False) if messages else st.container(border=False)
    with box:
        if not messages:
            st.chat_message("assistant", avatar="🤖").markdown(
                "Hi! Ask me about heat stress on your site, what the PET, PMV, PPD, SET, RWS "
                "and CE values mean, or how to keep your crew safe and productive."
            )
        for m in messages:
            st.chat_message(m["role"], avatar="👷" if m["role"] == "user" else "🤖").markdown(m["content"])

    suggestion = None
    if not messages:
        cols = st.columns(2)
        for i, (label, question) in enumerate(SUGGESTED_QUESTIONS):
            if cols[i % 2].button(label, key=f"{key}_suggest_{i}", help=question):
                suggestion = question
    prompt = st.chat_input("Ask about heat stress, PET, work-rest schedules...", key=f"{key}_input") or suggestion
    st.caption("Powered by Google Gemini (free tier). AI answers can be wrong and are not medical advice.")

    if not prompt:
        return
    if sum(m["role"] == "user" for m in messages) >= MAX_QUESTIONS_PER_SESSION:
        st.info("You've reached the question limit for this session. Clear the chat to start over.")
        return

    messages.append({"role": "user", "content": prompt})
    with box:
        st.chat_message("user", avatar="👷").markdown(prompt)
        with st.chat_message("assistant", avatar="🤖"):
            try:
                reply = st.write_stream(_stream_reply(api_key, _system_prompt(context), messages))
            except ChatError as e:
                messages.pop()  # let the user ask the same question again
                st.error(str(e))
                return
    messages.append({"role": "assistant", "content": reply or "Sorry, I couldn't answer that. Please rephrase."})
    st.rerun()
