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
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------
# READ API KEY FROM STREAMLIT SECRETS
# -------------------------------------------------
try:
    PPLX_API_KEY = st.secrets["PPLX_API_KEY"]
except:
    PPLX_API_KEY = None  # App will show warning

# -------------------------------------------------
# LOAD ICD-10 DATA
# -------------------------------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")

    # Normalize columns
    df.columns = df.columns.str.lower().str.strip()

    # Columns from your Excel file
    df = df.rename(columns={
        "code": "code",
        "short description (valid icd-10 fy2025)": "short_desc",
        "long description (valid icd-10 fy2025)": "long_desc",
    })

    return df[["code", "short_desc", "long_desc"]]

icd_df = load_icd10()

# -------------------------------------------------
# AI FUNCTION (NO NEED TO MODIFY)
# -------------------------------------------------
def ask_ai(prompt):
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
        res = requests.post(url, headers=headers, json=payload)
        if "json" not in res.headers.get("Content-Type", ""):
            return "⚠️ Unexpected response from AI service."

        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"API Error: {e}"

# -------------------------------------------------
# HERO HEADER
# -------------------------------------------------
st.markdown(
    """
<div class="hero-card">
  <div class="hero-title">ICD-10 Lookup Dashboard</div>
  <div class="hero-subtitle">
    Fast, modern, professional ICD-10 search with built-in AI explanations.
  </div>
  <div class="hero-badge">
    Powered by Hanvion Health • 2026 ICD-10 update
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# SEARCH BAR
# -------------------------------------------------
st.markdown('<div class="soft-card">', unsafe_allow_html=True)
query = st.text_input("Search ICD-10 code or diagnosis name:")
st.markdown('</div>', unsafe_allow_html=True)

# Filter results
df_filtered = icd_df.copy()

if query:
    df_filtered = df_filtered[
        df_filtered["code"].str.contains(query, case=False, na=False)
        | df_filtered["short_desc"].str.contains(query, case=False, na=False)
        | df_filtered["long_desc"].str.contains(query, case=False, na=False)
    ]

st.markdown(
    f'<div class="info-bar">Showing {len(df_filtered)} matching ICD-10 codes</div>',
    unsafe_allow_html=True,
)

# -------------------------------------------------
# TABLE + AI PANEL
# -------------------------------------------------
col1, col2 = st.columns([2, 1.4])

with col1:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("### Results")
    st.dataframe(df_filtered, hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("### AI Explanation")

    if df_filtered.empty:
        st.write("Search for a code to enable AI explanations.")
    else:
        selected = st.selectbox(
            "Select a code:",
            df_filtered["code"],
            index=0
        )

        row = df_filtered[df_filtered["code"] == selected].iloc[0]

        st.write(f"**{row['code']} — {row['short_desc']}**")

        mode = st.radio(
            "Explanation type:",
            ["Patient-friendly", "Clinical"],
            horizontal=True,
        )

        if st.button("Generate Explanation"):
            with st.spinner("Generating AI explanation..."):
                if mode == "Patient-friendly":
                    prompt = f"""
                    Explain ICD-10 code {row['code']} ({row['long_desc']}) 
                    in simple patient-friendly language.
                    """
                else:
                    prompt = f"""
                    Provide a clinical explanation of ICD-10 code {row['code']} 
                    ({row['long_desc']}), including symptoms, diagnostics 
                    and typical management.
                    """

                result = ask_ai(prompt)
                st.markdown(f'<div class="ai-box">{result}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
