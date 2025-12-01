# icd10_lookup_app.py
# Hanvion Health · ICD-10 Explorer (UI v2 + optional Perplexity AI)

import os
import json
import requests
import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    page_icon="💠",
    layout="wide",
)

# -------------------------------------------------------------------
# Hanvion UI v2.0 – global CSS
# -------------------------------------------------------------------
def inject_hanvion_css():
    st.markdown(
        """
        <style>
        /* --- Global layout --- */
        .stApp {
            background: #f5f5f7;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                         system-ui, "Segoe UI", sans-serif;
        }
        .block-container {
            padding-top: 1.5rem;
            max-width: 1200px;
        }

        /* --- Top brand bar --- */
        .hanvion-topbar {
            background: linear-gradient(90deg, #7b0016, #b30024);
            color: #ffffff;
            padding: 18px 24px;
            border-radius: 12px;
            margin-bottom: 18px;
            box-shadow: 0 14px 35px rgba(0, 0, 0, 0.16);
        }
        .hanvion-title {
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .hanvion-subtitle {
            font-size: 13px;
            margin-top: 4px;
            opacity: 0.86;
        }

        /* --- Section header --- */
        .hanvion-section {
            margin: 14px 0 10px 2px;
            font-size: 12px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #6b7280;
        }

        /* --- Card styling --- */
        .hanvion-card {
            background: #ffffff;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
            padding: 16px 18px 14px 18px;
            box-shadow: 0 6px 20px rgba(15, 23, 42, 0.07);
            margin-bottom: 14px;
        }
        .hanvion-chip {
            display: inline-block;
            background: #7b0016;
            color: #ffffff;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .hanvion-code-title {
            font-size: 18px;
            font-weight: 700;
            color: #111827;
        }
        .hanvion-muted {
            color: #6b7280;
            font-size: 12px;
        }
        .hanvion-meta {
            font-size: 12px;
            color: #4b5563;
            margin-top: 4px;
        }

        /* --- Buttons & expander tweaks --- */
        .stButton>button {
            border-radius: 999px;
            border: 1px solid #e5e7eb;
            background: #111827;
            color: #ffffff;
            padding: 4px 14px;
            font-size: 13px;
        }
        .stButton>button:hover {
            background: #1f2937;
            border-color: #d1d5db;
        }
        .streamlit-expanderHeader {
            font-size: 13px;
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background: #f9fafb;
            border-right: 1px solid #e5e7eb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_hanvion_css()

# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------
DATA_FILE = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"


@st.cache_data(show_spinner=True)
def load_icd10():
    """
    Load ICD-10 data from the CMS Excel file.
    Expected columns:
      CODE,
      SHORT DESCRIPTION (VALID ICD-10 FY2025),
      LONG DESCRIPTION (VALID ICD-10 FY2025),
      NF EXCL
    """
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Dataset '{DATA_FILE}' not found in the app folder."
        )

    df_raw = pd.read_excel(DATA_FILE, dtype=str).fillna("")

    # Normalise column names defensively
    col_map = {}
    for col in df_raw.columns:
        col_norm = col.strip().lower()
        if col_norm.startswith("code"):
            col_map["code"] = col
        elif "short description" in col_norm:
            col_map["short"] = col
        elif "long description" in col_norm:
            col_map["long"] = col
        elif "nf excl" in col_norm:
            col_map["nf_excl"] = col

    required = ["code", "short", "long"]
    missing = [r for r in required if r not in col_map]
    if missing:
        raise KeyError(
            f"Missing expected column(s) in Excel file: {missing}. "
            f"Found columns: {list(df_raw.columns)}"
        )

    df = pd.DataFrame(
        {
            "code": df_raw[col_map["code"]].astype(str).str.strip(),
            "short_description": df_raw[col_map["short"]].astype(str).str.strip(),
            "long_description": df_raw[col_map["long"]].astype(str).str.strip(),
            "nf_excl": df_raw.get(col_map.get("nf_excl", ""), ""),
        }
    )

    # Remove totally blank codes just in case
    df = df[df["code"] != ""].reset_index(drop=True)
    return df


# Try to load immediately so we fail fast if file is wrong
try:
    icd_df = load_icd10()
except Exception as e:
    st.error(f"Problem loading ICD-10 dataset: {e}")
    st.stop()

# -------------------------------------------------------------------
# Perplexity AI helpers (optional)
# -------------------------------------------------------------------
PPLX_DEFAULT_MODEL = "sonar-small-online"  # documented online model


def get_pplx_api_key():
    # 1) Streamlit secrets, 2) env var, 3) sidebar override
    key = ""
    try:
        key = st.secrets.get("PPLX_API_KEY", "")
    except Exception:
        key = ""

    if not key:
        key = os.getenv("PPLX_API_KEY", "")

    override = st.session_state.get("pplx_key_override", "")
    if override.strip():
        key = override.strip()

    return key


def call_perplexity(system_prompt: str, user_prompt: str, model: str) -> str:
    """
    Call Perplexity chat completions.
    Returns plain-text response or raises RuntimeError on serious errors.
    """
    api_key = get_pplx_api_key()
    if not api_key:
        raise RuntimeError(
            "No Perplexity API key configured. "
            "Add it in the sidebar to enable AI explanations."
        )

    endpoint = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 512,
    }

    try:
        resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=40)
    except Exception as exc:
        raise RuntimeError(f"Network / connection error calling Perplexity: {exc}")

    if resp.status_code != 200:
        # Pass back API message if present
        try:
            err_json = resp.json()
            msg = err_json.get("error", {}).get("message", str(err_json))
        except Exception:
            msg = resp.text
        raise RuntimeError(f"AI Error {resp.status_code}: {msg}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError("Unexpected response format from Perplexity API.")


def build_clinical_fallback(row):
    return (
        f"Educational summary for ICD-10 code **{row['code']}**:\n\n"
        f"- Short description: {row['short_description']}\n"
        f"- Long description: {row['long_description']}\n"
        f"- NF EXCL: {row['nf_excl'] or 'Not specified in this dataset.'}\n\n"
        "This is a high-level reference view of the diagnosis code and is "
        "not clinical guidance or billing advice."
    )


def build_patient_fallback(row):
    return (
        f"This code (**{row['code']}**) refers to:\n\n"
        f"**{row['short_description']}**.\n\n"
        "In simple terms, this describes a specific health condition that "
        "your doctor may use for documentation and insurance. "
        "For personalised medical questions, please talk with a licensed clinician."
    )


# -------------------------------------------------------------------
# Sidebar – AI & settings
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Hanvion Settings")

    st.markdown(
        "Use this explorer to search the official CMS ICD-10 list. "
        "AI explanations are optional and educational only."
    )

    st.markdown("---")
    st.markdown("##### AI (Perplexity – optional)")

    model_choice = st.selectbox(
        "Perplexity model",
        options=[
            PPLX_DEFAULT_MODEL,
            "sonar-medium-online",
        ],
        index=0,
        help="These are documented Perplexity Sonar online models. "
             "If a model gives 'invalid_model', try the other option.",
    )
    st.session_state["pplx_model"] = model_choice

    key_input = st.text_input(
        "Perplexity API key",
        type="password",
        help="Optional. If empty, AI explanations will fall back to static summaries.",
    )
    st.session_state["pplx_key_override"] = key_input

    st.markdown("---")
    st.caption("Hanvion Health · ICD-10 Explorer · Educational use only")


# -------------------------------------------------------------------
# Main UI
# -------------------------------------------------------------------
# Hanvion top bar
st.markdown(
    """
    <div class="hanvion-topbar">
        <div class="hanvion-title">HANVION&nbsp;HEALTH</div>
        <div class="hanvion-subtitle">
            ICD-10 Explorer · Official CMS dataset · Educational explanations only
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hanvion-section">Search</div>', unsafe_allow_html=True)

col_search, col_per_page, col_page = st.columns([4, 1.5, 1.2])

with col_search:
    query = st.text_input(
        "Search by ICD-10 code or diagnosis",
        placeholder="Example: J4520, asthma, fracture, diabetes",
        label_visibility="collapsed",
    )

with col_per_page:
    per_page = st.number_input(
        "Results per page",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        label_visibility="collapsed",
    )

with col_page:
    page_num = st.number_input(
        "Page",
        min_value=1,
        value=1,
        step=1,
        label_visibility="collapsed",
    )

# If no search yet, show friendly empty state and stop
if not query.strip():
    st.info(
        "Start by typing an ICD-10 code or diagnosis above. "
        "Results and explanations will appear once you search."
    )
    st.stop()

# -------------------------------------------------------------------
# Filtering & pagination
# -------------------------------------------------------------------
q = query.strip()

mask = (
    icd_df["code"].str.contains(q, case=False)
    | icd_df["short_description"].str.contains(q, case=False)
    | icd_df["long_description"].str.contains(q, case=False)
)

filtered = icd_df[mask].reset_index(drop=True)
total = len(filtered)

if total == 0:
    st.warning("No ICD-10 codes matched your search. Try another keyword or code.")
    st.stop()

max_page = max(1, (total - 1) // int(per_page) + 1)
page_num = min(max_page, int(page_num))

start_idx = (page_num - 1) * int(per_page)
end_idx = min(start_idx + int(per_page), total)
page_df = filtered.iloc[start_idx:end_idx].reset_index(drop=True)

st.caption(f"Showing {start_idx + 1}–{end_idx} of {total} matching codes (page {page_num} of {max_page}).")

# -------------------------------------------------------------------
# Helper – render one ICD-10 card
# -------------------------------------------------------------------
def render_icd_card(row):
    code = row["code"]
    short = row["short_description"]
    long = row["long_description"]
    nf_excl = row["nf_excl"]

    # Card header
    st.markdown(
        f"""
        <div class="hanvion-card">
            <div class="hanvion-chip">{code}</div>
            <div class="hanvion-code-title">{short}</div>
            <div class="hanvion-meta">
                {long}
            </div>
        """,
        unsafe_allow_html=True,
    )

    # NF EXCL
    nf_text = nf_excl.strip()
    if nf_text:
        st.markdown(
            f'<p class="hanvion-muted" style="margin-top:6px;"><strong>NF EXCL:</strong> {nf_text}</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="hanvion-muted" style="margin-top:6px;">NF EXCL: Not specified in this dataset.</p>',
            unsafe_allow_html=True,
        )

    # Clinical explanation
    with st.expander("Clinical explanation (educational only)", expanded=False):
        st.caption(
            "These summaries are for learning only and are not medical advice, "
            "coding guidance, or billing recommendations."
        )
        clinical_prompt = st.text_area(
            "Your clinical question (optional)",
            value=f"Explain the clinical meaning, common presentation, and key management "
                  f"considerations for ICD-10 code {code}: {short}.",
            key=f"clinical_q_{code}",
            label_visibility="collapsed",
        )
        if st.button(f"Explain clinically: {code}", key=f"btn_clinical_{code}"):
            try:
                answer = call_perplexity(
                    system_prompt=(
                        "You are a clinical educator explaining ICD-10 diagnosis codes "
                        "for healthcare professionals. Provide concise, structured, "
                        "evidence-informed explanations. Do not give patient-specific advice."
                    ),
                    user_prompt=clinical_prompt,
                    model=st.session_state.get("pplx_model", PPLX_DEFAULT_MODEL),
                )
                st.markdown(answer)
            except RuntimeError as err:
                st.error(str(err))
                st.markdown(build_clinical_fallback(row))

    # Patient-friendly explanation
    with st.expander("Patient-friendly explanation (educational only)", expanded=False):
        st.caption(
            "Summaries are simplified and may not fit every situation. "
            "They are not a substitute for speaking with a clinician."
        )
        patient_prompt = st.text_area(
            "Your question (optional)",
            value=(
                f"Explain ICD-10 code {code} ({short}) in simple language for a patient, "
                "including what it usually means, common symptoms, and when a patient "
                "should talk to their doctor. Avoid treatment recommendations."
            ),
            key=f"patient_q_{code}",
            label_visibility="collapsed",
        )
        if st.button(f"Explain simply: {code}", key=f"btn_patient_{code}"):
            try:
                answer = call_perplexity(
                    system_prompt=(
                        "You explain medical concepts to patients in clear, calm, "
                        "non-alarming language. You avoid giving medical advice or "
                        "treatment plans. Always recommend speaking to a licensed clinician "
                        "for personal concerns."
                    ),
                    user_prompt=patient_prompt,
                    model=st.session_state.get("pplx_model", PPLX_DEFAULT_MODEL),
                )
                st.markdown(answer)
            except RuntimeError as err:
                st.error(str(err))
                st.markdown(build_patient_fallback(row))

    # Compare with another ICD-10 code
    with st.expander("Compare with another ICD-10 code", expanded=False):
        all_codes = icd_df["code"].tolist()
        compare_code = st.selectbox(
            "Select a code to compare with",
            options=[c for c in all_codes if c != code],
            key=f"compare_{code}",
        )
        other = icd_df[icd_df["code"] == compare_code].iloc[0]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{code} — {short}**")
            st.write(long)
        with c2:
            st.markdown(f"**{other['code']} — {other['short_description']}**")
            st.write(other["long_description"])

    # Close card div
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------------------------------------------
# Render all cards on this page
# -------------------------------------------------------------------
for _, row in page_df.iterrows():
    render_icd_card(row)
