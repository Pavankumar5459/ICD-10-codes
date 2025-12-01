import streamlit as st
import pandas as pd
import requests
import os

# =========================================================
#  Hanvion Health ICD-10 Explorer (Final Production Build)
# =========================================================

st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    page_icon="💠",
    layout="wide",
)

# =========================================================
#  LOAD CMS ICD-10 DATASET
# =========================================================
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str,
        engine="openpyxl"
    ).fillna("")

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
    )

    final = pd.DataFrame()
    final["code"] = df["code"]
    final["short"] = df["short_description_valid_icd-10_fy2025"]
    final["long"] = df["long_description_valid_icd-10_fy2025"]
    final["exclusions"] = df["nf_excl"]

    return final


df = load_icd10()

# =========================================================
#  HANVION BEAUTIFUL UI
# =========================================================
st.markdown("""
<style>
/* Banner */
.h-banner {
    width:100%;
    padding:40px 20px;
    border-radius:18px;
    background: linear-gradient(90deg, #004c97, #0073cf);
    color:white;
    text-align:center;
    margin-top:25px;
    margin-bottom:35px;
}

/* Result Card */
.result-card {
    background:#fafaff;
    border:1px solid #e0e6ef;
    padding:22px;
    border-radius:14px;
    margin-bottom:22px;
}

.h-muted { 
    color:#6b7280;
    font-size:14px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
#  PERPLEXITY AI FUNCTION (FINAL)
# =========================================================
def ask_ai(prompt):
    api_key = st.secrets["PPLX_API_KEY"]

    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sonar-medium-online",   # VALID & high-quality
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.35
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        data = r.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return f"AI Error: {data}"

    except Exception as e:
        return f"AI Error: {e}"

# =========================================================
#  HEADER
# =========================================================
st.markdown("""
<div class="h-banner">
    <h1>Hanvion Health · ICD-10 Explorer</h1>
    <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
#  SEARCH INPUTS
# =========================================================
query = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

results_per_page = st.number_input("Results per page", 5, 100, 20)
page = st.number_input("Page", 1, 999999, 1)

# =========================================================
#  SEARCH LOGIC
# =========================================================
if query.strip() == "":
    st.info("💙 Begin typing to search ICD-10 codes…")
    st.stop()

q = query.lower().strip()

filtered = df[
    df["code"].str.lower().str.contains(q)
    | df["short"].str.lower().str.contains(q)
    | df["long"].str.lower().str.contains(q)
]

total = len(filtered)
start = (page - 1) * results_per_page
end = start + results_per_page
subset = filtered.iloc[start:end]

st.write(f"Showing **{start+1}–{min(end, total)}** of **{total}** results.")

# =========================================================
#  DISPLAY RESULTS
# =========================================================
for _, row in subset.iterrows():

    st.markdown(
        f"""
        <div class="result-card">
            <h3>{row['code']} — {row['short']}</h3>
            <p class="h-muted">{row['long']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # Clinical Explanation
    # -----------------------------------------------------
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}", key=f"c-{row['code']}"):
            prompt = f"""
            Provide a detailed clinical explanation for ICD-10 code {row['code']}.

            Short description: {row['short']}
            Long description: {row['long']}
            Exclusions: {row['exclusions']}

            Include:
            - Clinical meaning
            - Typical presentation
            - Risk factors
            - How clinicians classify this
            - How it differs from similar ICD codes
            Educational only, not medical advice.
            """

            st.write(ask_ai(prompt))

    # -----------------------------------------------------
    # Patient-friendly explanation
    # -----------------------------------------------------
    with st.expander("Patient-friendly explanation"):
        if st.button(f"Explain simply: {row['code']}", key=f"p-{row['code']}"):
            prompt = f"""
            Explain ICD-10 code {row['code']} in simple, easy-to-understand language.

            What the condition means:
            {row['long']}

            Include:
            - What the condition is
            - Common symptoms
            - When to seek help
            - How people usually manage it
            Not medical advice.
            """
            st.write(ask_ai(prompt))

    # -----------------------------------------------------
    # Compare Codes
    # -----------------------------------------------------
    with st.expander("Compare with another ICD-10 code"):
        cmp = st.text_input(f"Enter another ICD-10 code to compare with {row['code']}", key=f"cmp-{row['code']}")

        if cmp:
            prompt = f"""
            Compare ICD-10 code {row['code']} with {cmp}.

            For each code, list:
            - Definition
            - Severity
            - Clinical use
            - Differences
            - When each is used
            """
            st.write(ask_ai(prompt))

    st.markdown("---")
