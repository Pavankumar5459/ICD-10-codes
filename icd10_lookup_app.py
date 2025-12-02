import streamlit as st
import pandas as pd
import requests

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="ICD-10 Lookup Dashboard – Hanvion Health",
    page_icon="🩺",
    layout="wide",
)

# -------------------------------------------------
# GLOBAL STYLING
# -------------------------------------------------
CUSTOM_CSS = """
<style>
.stApp {
    background-color: #f4f7fb;
    font-family: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI", sans-serif;
}

.block-container {
    padding-top: 1.5rem;
}

/* Hero card */
.hero-card {
    background: linear-gradient(135deg, #004c97, #0077b6);
    border-radius: 1.5rem;
    padding: 2.5rem 3rem;
    color: #ffffff;
    box-shadow: 0 18px 35px rgba(15, 23, 42, 0.4);
    margin-bottom: 1.75rem;
}
.hero-title {
    font-size: 2.1rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.hero-subtitle {
    font-size: 0.98rem;
    opacity: 0.95;
    max-width: 640px;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    background-color: rgba(15, 23, 42, 0.3);
    font-size: 0.75rem;
    margin-top: 0.9rem;
}

/* Soft cards */
.soft-card {
    background-color: #ffffff;
    border-radius: 1rem;
    padding: 1.3rem 1.4rem;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    margin-bottom: 1rem;
}

/* Info bar */
.info-bar {
    background-color: #f1f5f9;
    border-radius: 0.8rem;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    margin: 0.3rem 0 0.8rem 0;
}

/* AI box */
.ai-box {
    background-color: #f8fafc;
    border-radius: 0.8rem;
    padding: 0.9rem 1rem;
    font-size: 0.9rem;
    border: 1px solid #e2e8f0;
    margin-top: 0.7rem;
}
.ai-box h4 {
    margin-top: 0;
    margin-bottom: 0.4rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------
# READ API KEY FROM STREAMLIT SECRETS
# -------------------------------------------------
try:
    PPLX_API_KEY = st.secrets["PPLX_API_KEY"]
except Exception:
    PPLX_API_KEY = None  # will show a warning in the UI

# -------------------------------------------------
# LOAD ICD-10 DATA
# -------------------------------------------------
@st.cache_data
def load_icd10():
    # Excel file must be in the same folder as this script
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")

    # Normalize columns
    df.columns = df.columns.str.lower().str.strip()

    # Match your file's real column names
    code_col = "code"
    short_col = "short description (valid icd-10 fy2025)"
    long_col = "long description (valid icd-10 fy2025)"
    nf_col = "nf excl" if "nf excl" in df.columns else None

    # Basic presence check
    missing = [c for c in [code_col, short_col, long_col] if c not in df.columns]
    if missing:
        st.error(f"Expected columns not found in Excel: {missing}")
        st.write("Available columns:", df.columns.tolist())
        st.stop()

    # Classify codes as Included vs Excluded using NF EXCL
    if nf_col:
        def classify(x):
            x_str = str(x).strip()
            return "Excluded" if x_str not in ("", "nan", "NaN") else "Included"
        df["code_type"] = df[nf_col].apply(classify)
    else:
        df["code_type"] = "Included"

    tidy = df[[code_col, short_col, long_col, "code_type"]].copy()
    tidy = tidy.rename(
        columns={
            code_col: "code",
            short_col: "short_desc",
            long_col: "long_desc",
        }
    )
    tidy = tidy.sort_values("code").reset_index(drop=True)
    return tidy

icd_df = load_icd10()

# -------------------------------------------------
# AI CALL HELPERS (YOU DON'T NEED TO TOUCH THIS)
# -------------------------------------------------
def call_perplexity(prompt: str) -> str:
    """Low-level API call to Perplexity."""
    if not PPLX_API_KEY:
        return "⚠️ AI is not configured. Add PPLX_API_KEY in Streamlit Secrets."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "pplx-70b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=40)

        # If Cloudflare / HTML happened
        if "json" not in resp.headers.get("Content-Type", ""):
            return f"⚠️ Unexpected response from AI service:\n\n{resp.text[:800]}"

        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API Error: {e}"

@st.cache_data(show_spinner=False)
def get_ai_explanation(code: str, long_desc: str, mode: str) -> str:
    """
    Cached AI explanation so it's fast.
    mode = "patient" or "clinical"
    """
    if mode == "clinical":
        prompt = f"""
        You are a clinical documentation expert.

        Provide a concise, medically accurate clinical explanation of ICD-10 code {code} ({long_desc}).
        Include:
        - Clinical definition and context
        - Common causes / risk factors
        - Typical symptoms and diagnostic considerations
        - High-level management or treatment overview

        Audience: clinicians and coding professionals.
        Keep it structured with short paragraphs or bullet points, under 220 words.
        """
    else:
        prompt = f"""
        Explain ICD-10 code {code} ({long_desc}) in friendly, simple language for patients.

        Include:
        - What this condition means in plain words
        - Common symptoms people might notice
        - When they should contact a doctor or seek urgent care
        - Reassuring, practical guidance (no guarantees, no diagnosis)

        Avoid medical jargon. Use clear language and keep it under 200 words.
        """

    return call_perplexity(prompt.strip())

# -------------------------------------------------
# HERO HEADER
# -------------------------------------------------
st.markdown(
    """
<div class="hero-card">
  <div class="hero-title">ICD-10 Lookup Dashboard</div>
  <div class="hero-subtitle">
    Search the latest ICD-10 diagnosis codes and generate both patient-friendly and clinical explanations in one place.
  </div>
  <div class="hero-badge">
    Hanvion Health • 2026 ICD-10 Update • AI Assisted
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if not PPLX_API_KEY:
    st.warning("⚠️ AI explanations are disabled because `PPLX_API_KEY` is not set in Streamlit secrets.", icon="⚠️")

# -------------------------------------------------
# FILTER BAR (TYPE + SEARCH)
# -------------------------------------------------
top_left, top_right = st.columns([1.1, 2.1])

with top_left:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("**Code Type**")
    type_filter = st.selectbox(
        "Filter by type",
        ["All codes", "Included only", "Excluded only"],
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with top_right:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("**Search ICD-10 Code or Diagnosis**")
    query = st.text_input(
        "Search",
        placeholder="Example: E11, diabetes, fracture, asthma…",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# FILTER LOGIC
# -------------------------------------------------
df_filtered = icd_df.copy()

if type_filter == "Included only":
    df_filtered = df_filtered[df_filtered["code_type"] == "Included"]
elif type_filter == "Excluded only":
    df_filtered = df_filtered[df_filtered["code_type"] == "Excluded"]

if query:
    pattern = query.strip()
    df_filtered = df_filtered[
        df_filtered["code"].str.contains(pattern, case=False, na=False)
        | df_filtered["short_desc"].str.contains(pattern, case=False, na=False)
        | df_filtered["long_desc"].str.contains(pattern, case=False, na=False)
    ]

max_rows = 40
total_matches = len(df_filtered)
df_show = df_filtered.head(max_rows)

info_text = (
    f"Showing first {len(df_show)} of {total_matches} matching ICD-10 codes."
    if query
    else f"Showing first {len(df_show)} codes. Use search to narrow down."
)

st.markdown(
    f'<div class="info-bar">{info_text}</div>',
    unsafe_allow_html=True,
)

# -------------------------------------------------
# RESULTS + AI PANEL
# -------------------------------------------------
left_col, right_col = st.columns([2.2, 1.8])

with left_col:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("### ICD-10 Results")

    if df_show.empty:
        st.write("No matching codes. Try a different search or clear filters.")
    else:
        table = df_show.rename(
            columns={
                "code": "ICD-10 Code",
                "short_desc": "Short Description",
                "long_desc": "Long Description",
                "code_type": "Type",
            }
        )
        st.dataframe(table, hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("### AI Explanations (Patient + Clinical)")

    if df_show.empty:
        st.write("Select a search result to enable AI explanations.")
    else:
        selected_index = st.selectbox(
            "Choose a code:",
            df_show.index,
            format_func=lambda i: f"{df_show.loc[i, 'code']} — {df_show.loc[i, 'short_desc']}",
        )
        selected_row = df_show.loc[selected_index]

        st.write(f"**{selected_row['code']} — {selected_row['long_desc']}**")

        auto_generate = st.checkbox(
            "Auto-generate when I select a code",
            value=True,
            help="When enabled, both explanations load as soon as you choose a code.",
        )

        generate_clicked = st.button("Generate / Refresh explanations")

        patient_text = ""
        clinical_text = ""

        if auto_generate or generate_clicked:
            with st.spinner("Generating explanations with AI…"):
                patient_text = get_ai_explanation(
                    selected_row["code"],
                    selected_row["long_desc"],
                    mode="patient",
                )
                clinical_text = get_ai_explanation(
                    selected_row["code"],
                    selected_row["long_desc"],
                    mode="clinical",
                )

        if patient_text or clinical_text:
            st.markdown('<div class="ai-box">', unsafe_allow_html=True)
            st.markdown("<h4>🧑‍⚕️ Patient-friendly explanation</h4>", unsafe_allow_html=True)
            st.write(patient_text)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="ai-box">', unsafe_allow_html=True)
            st.markdown("<h4>📋 Clinical explanation</h4>", unsafe_allow_html=True)
            st.write(clinical_text)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("Turn on auto-generate or click the button to see both explanations.")

    st.markdown("</div>", unsafe_allow_html=True)
