# TER-ASC AI Assistant

An AI chat assistant for the [TER-ASC heat-stress app](https://terasc-construction-heat-analytics.streamlit.app/).
It explains PET, PMV, PPD, SET, RWS and CE, the heat-risk levels, the work-rest and
hydration guidance, and how to use the app. When it is given the current inputs and
predictions, it answers about the user's own situation ("what do my results mean?").

It runs on **Google Gemini 3.8 Flash**, Google's strongest model on the free tier
(no credit card needed). If that model hits its free limit, it automatically falls back
to Gemini 3.6 Flash, then Gemini 3.5 Flash-Lite.

| File | What it is |
|---|---|
| `terasc_chat.py` | **The chat itself.** The only file the TER-ASC app needs. |
| `app.py` | Standalone demo website around the chat (sidebar with sample conditions). |
| `requirements.txt` | Python packages. |
| `.streamlit/secrets.toml.example` | Template for the API key. |

## 1. Get a free Gemini API key

1. Go to <https://aistudio.google.com/apikey> and sign in with a Google account.
2. Click **Create API key** and copy it.

## 2. Run it on your computer

```bash
pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste your key into it, then:

```bash
streamlit run app.py
```

## 3. Put it online as its own website (free)

1. Create a GitHub repository and upload these files. Do **not** upload `secrets.toml` (`.gitignore` already excludes it).
2. Go to <https://share.streamlit.io>, click **Create app**, choose the repository, and set the main file to `app.py`.
3. Under **Advanced settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
4. Click **Deploy**. You get a link like `https://your-app-name.streamlit.app` to send for review.

## 4. Add it to the TER-ASC app (for the professor)

1. Copy `terasc_chat.py` next to the TER-ASC main script.
2. Add this line to the app's `requirements.txt`:
   ```
   google-genai>=2.0
   ```
3. In the Streamlit Cloud dashboard: **App settings → Secrets**, add `GEMINI_API_KEY = "..."`.
4. In the main script, add a tab and pass the values the app already computes. The names
   on the right are placeholders; use the app's own variable names:
   ```python
   from terasc_chat import render_chat

   tab_map, tab_vert, tab_prod, tab_safety, tab_ai = st.tabs(
       ["🗺️ PET Map", "📈 Vertical Analysis", "📊 Productivity", "📋 Safety Guide", "🤖 AI Assistant"]
   )
   ...
   with tab_ai:
       render_chat(context={
           "Air temperature (°C)": temp,
           "Relative humidity (%)": humidity,
           "Wind speed (m/s)": wind_speed,
           "Clothing insulation (clo)": clo,
           "Metabolic rate (met)": met,
           "Work type": work_type,
           "Working height (m)": height,
           "PET (°C)": pet,
           "Heat risk level": level,     # e.g. "HOT"
           "PMV": pmv,
           "PPD (%)": ppd,
           "SET (°C)": set_value,
           "RWS (m/s)": rws,
           "CE (°C)": ce,
       })
   ```
   `context` is optional, and any labels work. The assistant reads them as "current conditions".

Options: `render_chat(context, key="terasc_chat", height=460, style=True)`. `height` is the
chat box height in pixels. Set `style=False` to keep the app's own chat-bubble styling.

## Good to know

- **Free-tier limits.** Google sets request limits per model and per project. You can see
  the current numbers in AI Studio under *Rate limits*. Each visitor can ask up to 40
  questions per session (`MAX_QUESTIONS_PER_SESSION` in `terasc_chat.py`). If all models
  are busy, users see "try again in a minute" instead of an error page.
- **Privacy.** On the free tier, Google may use prompts to improve its products. Users
  shouldn't type personal or confidential information. A paid key removes this.
- **What it knows.** The app's facts, thresholds and safety guidance are written into
  `SYSTEM_PROMPT` in `terasc_chat.py`. If the app's rules change, update that text.
- **Changing the model.** Edit the `MODELS` list at the top of `terasc_chat.py`.
- AI answers can be wrong. The assistant tells users it is not medical advice and to
  call 911 for suspected heat stroke.
