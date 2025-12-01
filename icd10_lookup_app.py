import streamlit as st
import pandas as pd
import requests
import os

# =========================================================
#  Hanvion Health – ICD-10 Explorer (PPLX + CMS Dataset)
# =========================================================

st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    page_icon="💠",
    layout="wide",
)

# -------------------------
#  LOAD DATASET
# -------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str,
        engine="openpyxl"
    ).fillna("")

    # Normalize column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
    )

    # Expected CMS column names
    # CODE, SHORT DESCRIPTION (VALID ICD-10 FY2025), LONG DESCRIPTION (VALID ICD-10 FY2025), NF EXCL
    code_col = "code"
    short_col = "short_description_valid_icd-10_fy2025"
    long_col = "long_description_valid_icd-10_fy2025"
    excl_col = "nf_excl"

    final = pd.DataFrame()
    final["code"] = df[code_col].astype(str).str.strip()
    final["short"] = df[short_col].astype(str).str.strip()
    final["long"] = df[long_col].astype(str).str.strip()
    final["exclusions"] = df[excl_col].astype(str).str.strip()

    return final


df = load_icd10()


# =========================================================
#  HANVION THEME CSS
# =========================================================
HANVION_CSS = """
<style>

body, input, textarea, select {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
}

.h-banner {
    width:100%;
    padding:42px 20px;
    border-radius:18px;
    background: linear-gradient(90deg, #004c97, #0073cf);
    color:white;
    text-align:center;
    margin-top:40px;
    margin-bottom:30px;
}

.code-box {
    background:#f7f7fb;
    padding:22px;
    border-radius:12px;
    border:1px solid #e2e8f0;
    margin-top:10px;
}

.dark-mode .code-box {
    background:#1e293b !important;
    border-color:#334155 !important;
}

.result-card {
    background:#fafaff;
    border:1px solid #e2e8f0;
    padding:22px;
    border-radius:14px;
    margin-bottom:18px;
}

.dark-mode .result-card {
    background:#1e2533 !important;
    border-color:#334155 !important;
}

.h-muted {
    color:#6b7280;
}

.dark-mode .h-muted {
    color:#cbd5e1 !important;
}

</style>
"""

st.markdown(HANVION_CSS, unsafe_allow_html=True)


# =========================================================
#  PERPLEXITY AI FUNCTION (using PPLX_API_KEY)
# =========================================================
def ask_ai(prompt):
    """Uses Perplexity pplx-7b-chat with your secret key"""

    api_key = st.secrets["PPLX_API_KEY"]

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "pplx-7b-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        out = res.json()
        if "choices" in out:
            return out["choices"][0]["message"]["content"]
        else:
            return f"AI Error: {out}"
    except Exception as e:
        return f"AI Error: {e}"


# =========================================================
#  PAGE HEADER
# =========================================================
st.markdown(
    """
    <div class="h-banner">
        <h1>Hanvion Health · ICD-10 Explorer</h1>
        <p>Search official CMS ICD-10 codes with optional AI-powered educational explanations.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
#  SEARCH BAR
# =========================================================
query = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

results_per_page = st.number_input("Results per page", 5, 100, 20)
page = st.number_input("Page", 1, 999999, 1)


# =========================================================
#  RUN SEARCH
# =========================================================
if query.strip() == "":
    st.info("Begin typing above to search ICD-10 codes.")
    st.stop()

q = query.strip().lower()

filtered = df[
    df["code"].str.lower().str.contains(q)
    | df["short"].str.lower().str.contains(q)
    | df["long"].str.lower().str.contains(q)
]

total = len(filtered)
start = (page - 1) * results_per_page
end = start + results_per_page
page_df = filtered.iloc[start:end]

st.write(f"Showing {start+1}–{min(end, total)} of {total} results.\n")


# =========================================================
#  DISPLAY RESULTS
# =========================================================
for _, row in page_df.iterrows():
    st.markdown(
        f"""
        <div class='result-card'>
            <h3>{row['code']} — {row['short']}</h3>
            <p class='h-muted'>{row['long']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Clinical explanation (educational only)"):
        ask = st.button(f"Explain clinically: {row['code']}", key=f"c-{row['code']}")
        if ask:
            prompt = f"""
            Provide a clinical, medical explanation for ICD-10 code {row['code']}:
            {row['short']}
            {row['long']}

            Format:
            - Clinical meaning
            - Typical symptoms
            - How clinicians interpret this code
            - Why it matters
            - Not medical advice
            """
            out = ask_ai(prompt)
            st.write(out)

    with st.expander("Patient-friendly explanation"):
        ask2 = st.button(f"Explain simply: {row['code']}", key=f"p-{row['code']}")
        if ask2:
            prompt = f"""
            Explain ICD-10 code {row['code']} in simple, patient-friendly language.

            Include:
            - What the condition means
            - Common symptoms
            - When someone should contact a clinician
            - NOT medical advice
            """
            out = ask_ai(prompt)
            st.write(out)

    with st.expander("Compare with another ICD-10 code"):
        compare_query = st.text_input(
            f"Enter another ICD-10 code to compare with {row['code']}",
            key=f"cmp-{row['code']}"
        )
        if compare_query:
            prompt = f"""
            Compare ICD-10 code {row['code']} ({row['short']})
            with ICD-10 code {compare_query}.

            Include:
            - Difference in condition type
            - Severity differences
            - Body system affected
            - Situations where each is used
            - Educational only
            """
            out = ask_ai(prompt)
            st.write(out)

    st.markdown("---")
