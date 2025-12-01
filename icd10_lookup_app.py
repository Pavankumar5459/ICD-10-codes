import streamlit as st
import pandas as pd
import requests

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Hanvion Health • ICD-10 Explorer",
    page_icon="🩺",
    layout="wide"
)

# ============================================================
# DARK MODE TOGGLE
# ============================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Right-aligned toggle
col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️", help="Toggle dark mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode

dark = st.session_state.dark_mode

# ============================================================
# DARK / LIGHT THEME STYLES
# ============================================================
light_css = """
<style>
body { background-color: #f8fbff; }
.card {
    padding: 20px;
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e6e9ee;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.header {
    padding: 30px;
    border-radius: 14px;
    background: linear-gradient(135deg, #004a99, #0070cc);
    color: white;
    text-align: center;
    margin-bottom: 25px;
}
</style>
"""

dark_css = """
<style>
body { background-color: #0d1117; }
h1, h2, h3, label, p, span, div { color: #e6edf3 !important; }
.card {
    padding: 20px;
    background: #161b22;
    border-radius: 12px;
    border: 1px solid #30363d;
    box-shadow: 0 1px 4px rgba(0,0,0,0.5);
}
input, textarea, select, .stNumberInput > div > input {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
}
.header {
    padding: 30px;
    border-radius: 14px;
    background: linear-gradient(135deg, #00254d, #005a9c);
    color: white;
    text-align: center;
    margin-bottom: 25px;
}
</style>
"""

st.markdown(dark_css if dark else light_css, unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="header">
    <h1>Hanvion Health • ICD-10 Explorer</h1>
    <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATASET
# ============================================================
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")
    df = df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long",
        "NF EXCL": "nf"
    })
    return df

df = load_icd10()


# ============================================================
# AI (Perplexity)
# ============================================================
PPLX_MODEL = "pplx-7b-chat"

def ask_ai(prompt):
    key = st.session_state.get("pplx_api", "")
    if not key:
        return "**AI unavailable — enter Perplexity API key above.**"

    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": PPLX_MODEL, "messages": [{"role": "user", "content": prompt}]}
        )
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {str(e)}"


# ============================================================
# SEARCH UI
# ============================================================
search = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

results_per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 9999, 1)

st.session_state["pplx_api"] = st.text_input(
    "Perplexity API key (optional)",
    type="password"
)


# ============================================================
# SEARCH RESULTS
# ============================================================
if search.strip():
    filtered = df[
        df["code"].str.contains(search, case=False) |
        df["short"].str.contains(search, case=False) |
        df["long"].str.contains(search, case=False)
    ]

    total = len(filtered)
    start = (page - 1) * results_per_page
    end = start + results_per_page

    st.write(f"Showing **{start+1}–{min(end, total)}** of **{total} results**")

    for i, row in filtered.iloc[start:end].iterrows():
        st.markdown(
            f"""
            <div class='card'>
                <h3>{row["code"]} — {row["short"]}</h3>
                <p>{row["long"]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("Clinical explanation (educational only)"):
            if st.button(f"Explain clinically: {row['code']}", key=f"clin{i}"):
                st.write(ask_ai(f"Explain ICD-10 code {row['code']} clinically."))

        with st.expander("Explain in simple words"):
            if st.button(f"Explain simply: {row['code']}", key=f"simp{i}"):
                st.write(ask_ai(f"Explain ICD-10 code {row['code']} in simple language."))

else:
    st.info("Begin typing above to search ICD-10 codes.")

