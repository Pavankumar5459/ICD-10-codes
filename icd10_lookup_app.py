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
# GLOBAL STYLING (to match your screenshot style)
# -------------------------------------------------
CUSTOM_CSS = """
<style>
.stApp {
    background-color: #f4f7fb;
    font-family: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI", sans-serif;
}

/* Remove default padding at top */
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
.hero-link {
    margin-top: 0.5rem;
    font-size: 0.8rem;
}
.hero-link a {
    color: #e0f4ff;
    text-decoration: underline;
}

/* Soft cards */
.soft-card {
    background-color: #ffffff;
    border-radius: 1rem;
    padding: 1.3rem 1.4rem;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    margin-bottom: 1rem;
}

/* Section titles */
.section-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
}

/* Little status chips */
.status-chip {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    background-color: #e0f2fe;
    color: #075985;
}

/* Results info bar */
.info-bar {
    background-color: #f1f5f9;
    border-radius: 0.8rem;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    margin: 0.3rem 0 0.8rem 0;
}

/* AI output box */
.ai-box {
    background-color: #f8fafc;
    border-radius: 0.8rem;
    padding: 0.9rem 1rem;
    font-size: 0.9rem;
    border: 1px solid #e2e8f0;
    margin-top: 0.7rem;
}

/* Make dataframes a bit cleaner */
.dataframe tbody tr th {
    font-size: 0.85rem;
}
.dataframe tbody td {
    font-size: 0.85rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------
# API KEY (safe)
# -------------------------------------------------
try:
    PPLX_API_KEY = st.secrets["PPLX_API_KEY"]
except Exception:
    PPLX_API_KEY = None

# -------------------------------------------------
# LOAD ICD-10 DATA
# -------------------------------------------------
@st.cache_data
def load_icd10():
    # Reads your CMS Excel file (first sheet)
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")

    # Normalize columns to lower-case
    df.columns = df.columns.str.lower().str.strip()

    # Match actual columns from your screenshot
    code_col = "code"
    short_col = "short description (valid icd-10 fy2025)"
    long_col = "long description (valid icd-10 fy2025)"
    nf_col = "nf excl"  # indicates excluded / non-covered

    missing = [c for c in [code_col, short_col, long_col] if c not in df.columns]
    if missing:
        st.error(f"Expected columns missing in Excel: {missing}")
        st.write("Available columns:", df.columns.tolist())
        st.stop()

    # Classify codes as Included vs Excluded using NF EXCL column
    if nf_col in df.columns:
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

    # For speed, sort once
    tidy = tidy.sort_values("code").reset_index(drop=True)
    return tidy


icd_df = load_icd10()

# -------------------------------------------------
# PERPLEXITY API (backend only)
# -------------------------------------------------
def call_perplexity(prompt: str) -> str:
    if not PPLX_API_KEY:
        return "⚠️ AI is not configured (missing `PPLX_API_KEY` in Streamlit secrets)."

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

        # If Cloudflare / HTML came back
        if "json" not in resp.headers.get("Content-Type", ""):
            return f"API Error (non-JSON response):\n\n{resp.text[:1500]}"

        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API Error: {e}"


@st.cache_data(show_spinner=False)
def get_ai_explanation(code: str, long_desc: str, mode: str) -> str:
    """Cache AI results by code + mode to keep it fast & cheap."""
    if mode == "clinical":
        prompt = f"""
        You are a clinical documentation expert.

        Provide a concise, medically accurate clinical explanation of ICD-10 code {code} ({long_desc}).
        Include:
        - Clinical definition
        - Common causes / risk factors
        - Key symptoms and diagnostic considerations
        - High-level treatment / management overview

        Audience: clinicians and coding professionals.
        Keep the response clear, structured, and under 220 words.
        """
    else:  # patient
        prompt = f"""
        Explain ICD-10 code {code} ({long_desc}) in friendly, simple language for patients.

        Include:
        - What this condition means in plain words
        - Typical symptoms people may notice
        - When they should contact a doctor or seek urgent care
        - Reassuring, practical guidance (no promises, no diagnosis)

        Avoid medical jargon. Use short paragraphs and bullet points where helpful.
        Keep it under 200 words.
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
    Search Included &amp; Excluded ICD-10 diagnosis codes (CMS 2026 update) with Hanvion Health's intelligent lookup tool.
  </div>
  <div class="hero-badge">
    <span>⚕️ Powered by Hanvion Health</span>
  </div>
  <div class="hero-link">
    Visit: <a href="https://hanvionhealth.com" target="_blank">hanvionhealth.com</a>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# FILTER + SEARCH AREA
# -------------------------------------------------
top_col1, top_col2 = st.columns([1.1, 2.1])

with top_col1:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Select Code Type</div>', unsafe_allow_html=True)

    code_type_option = st.selectbox(
        "Choose ICD-10 Code Category",
        ["All codes", "Included codes only", "Excluded codes only"],
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with top_col2:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Search ICD-10 Code or Diagnosis</div>',
        unsafe_allow_html=True,
    )
    search_text = st.text_input(
        "Search Diagnosis Name or ICD-10 Code:",
        placeholder="Example: J45, asthma, fracture, diabetes…",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# FILTER LOGIC
# -------------------------------------------------
df_filtered = icd_df.copy()

if code_type_option == "Included codes only":
    df_filtered = df_filtered[df_filtered["code_type"] == "Included"]
elif code_type_option == "Excluded codes only":
    df_filtered = df_filtered[df_filtered["code_type"] == "Excluded"]

if search_text:
    pattern = search_text.strip()
    df_filtered = df_filtered[
        df_filtered["code"].str.contains(pattern, case=False, na=False)
        | df_filtered["short_desc"].str.contains(pattern, case=False, na=False)
        | df_filtered["long_desc"].str.contains(pattern, case=False, na=False)
    ]

# Limit rows for speed
max_rows = 25
total_matches = len(df_filtered)
df_show = df_filtered.head(max_rows)

# Info bar
info_msg = (
    f"Showing first {len(df_show)} of {total_matches} matching ICD-10 codes."
    if search_text
    else f"Start typing a keyword to search ICD-10 codes. Showing the first {len(df_show)} codes by default."
)

st.markdown(
    f'<div class="info-bar">{info_msg}</div>',
    unsafe_allow_html=True,
)

# -------------------------------------------------
# RESULTS TABLE + AI PANEL
# -------------------------------------------------
bottom_col1, bottom_col2 = st.columns([2.3, 1.7])

with bottom_col1:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Results</div>', unsafe_allow_html=True)

    if df_show.empty:
        st.write("No matching ICD-10 codes found. Try a different keyword.")
    else:
        # Cleaner table for user
        table = df_show.rename(
            columns={
                "code": "ICD-10 Code",
                "short_desc": "Short Description",
                "long_desc": "Long Description",
                "code_type": "Type",
            }
        )
        st.dataframe(table, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with bottom_col2:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">AI-Powered Explanation</div>', unsafe_allow_html=True)

    if df_show.empty:
        st.write("Search for a code to enable AI explanations.")
    else:
        # Let user pick a row from the filtered result set
        idx = st.selectbox(
            "Choose a code to explain:",
            df_show.index,
            format_func=lambda i: f"{df_show.loc[i, 'code']} — {df_show.loc[i, 'short_desc']}",
        )
        selected = df_show.loc[idx]

        st.markdown(
            f"**{selected['code']} — {selected['long_desc']}**",
            unsafe_allow_html=True,
        )

        mode = st.radio(
            "Explanation type:",
            ["Patient-friendly", "Clinical (professional)"],
            horizontal=True,
        )

        if st.button("Generate AI explanation"):
            with st.spinner("Generating explanation with AI…"):
                if mode.startswith("Clinical"):
                    text = get_ai_explanation(
                        selected["code"], selected["long_desc"], mode="clinical"
                    )
                else:
                    text = get_ai_explanation(
                        selected["code"], selected["long_desc"], mode="patient"
                    )

            st.markdown(f'<div class="ai-box">{text}</div>', unsafe_allow_html=True)
        else:
            st.caption("Select a code and click the button to see AI summary.")

    st.markdown("</div>", unsafe_allow_html=True)
