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
if "dark" not in st.session_state:
    st.session_state.dark = False

top_left, top_right = st.columns([9,1])
with top_right:
    if st.button("🌙" if not st.session_state.dark else "☀️"):
        st.session_state.dark = not st.session_state.dark


# ============================================================
# HANVION PREMIUM CSS (LIGHT + DARK)
# ============================================================
LIGHT = """
<style>
body { background-color:#f6f9fc; }

.header-box {
    padding:35px;
    border-radius:16px;
    background:linear-gradient(135deg,#0055aa,#0077cc);
    color:white;
    text-align:center;
    margin-bottom:35px;
}

.input-box input, .input-box select, textarea {
    background:white !important;
    color:#111 !important;
    border:1px solid #d7dce3 !important;
    border-radius:10px !important;
    padding:10px !important;
}

.card {
    background:white;
    padding:20px;
    border-radius:14px;
    border:1px solid #e2e8f0;
    box-shadow:0 2px 6px rgba(0,0,0,0.06);
    margin-bottom:12px;
}
</style>
"""

DARK = """
<style>
body { background-color:#0e131a; }

h1,h2,h3,h4,label,p,span,div { color:#e4e9f0 !important; }

.header-box {
    padding:35px;
    border-radius:16px;
    background:linear-gradient(135deg,#003a6f,#005a9c);
    color:white !important;
    text-align:center;
    margin-bottom:35px;
}

.input-box input, .input-box select, textarea {
    background:#1a212c !important;
    color:#e4e9f0 !important;
    border:1px solid #2e3a48 !important;
    border-radius:10px !important;
    padding:10px !important;
}

.card {
    background:#151c25;
    padding:20px;
    border-radius:14px;
    border:1px solid #2c3643;
    box-shadow:0 2px 6px rgba(0,0,0,0.45);
    margin-bottom:12px;
}
</style>
"""

st.markdown(DARK if st.session_state.dark else LIGHT, unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="header-box">
    <h1>Hanvion Health • ICD-10 Explorer</h1>
    <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATA
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
# AI (PERPLEXITY)
# ============================================================
MODEL = "pplx-7b-chat"

def perplexity(prompt):
    key = st.session_state.get("pplx", "")
    if not key:
        return "Enter Perplexity API key above."
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": MODEL, "messages":[{"role":"user","content":prompt}]}
        )
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {str(e)}"


# ============================================================
# SEARCH UI
# ============================================================
with st.container():
    st.markdown('<div class="input-box">', unsafe_allow_html=True)
    search = st.text_input("Search ICD-10 code or diagnosis", placeholder="Example: J45, asthma, fracture, diabetes…")
    st.markdown('</div>', unsafe_allow_html=True)

colA, colB = st.columns(2)

with colA:
    results_per_page = st.number_input("Results per page", 5, 50, 20)

with colB:
    page = st.number_input("Page", 1, 5000, 1)

st.markdown('<div class="input-box">', unsafe_allow_html=True)
st.session_state["pplx"] = st.text_input("Perplexity API key (optional)", type="password")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# RESULTS
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

    st.write(f"Showing **{start+1}–{min(end,total)}** of **{total}** results")

    for i, row in filtered.iloc[start:end].iterrows():

        st.markdown(f"""
        <div class="card">
            <h3>{row['code']} — {row['short']}</h3>
            <p>{row['long']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Clinical explanation (educational only)"):
            if st.button(f"Explain clinically: {row['code']}", key=f"clin{i}"):
                st.write(perplexity(f"Explain ICD-10 code {row['code']} clinically."))

        with st.expander("Explain in simple words"):
            if st.button(f"Explain simply: {row['code']}", key=f"simp{i}"):
                st.write(perplexity(f"Explain ICD-10 {row['code']} in simple patient language."))

else:
    st.info("Begin typing above to search ICD-10 codes.")
