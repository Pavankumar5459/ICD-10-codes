import streamlit as st
import pandas as pd
import requests
import os

# =========================================================
#  Hanvion Health – ICD-10 Explorer (Perplexity AI)
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

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
    )

    code_col = "code"
    short_col = "short_description_valid_icd-10_fy2025"
    long_col = "long_description_valid_icd-10_fy2025"
    excl_col = "nf_excl"

    final = pd.DataFrame()
    final["code"] = df[code_col].astype(str)
    final["short"] = df[short_col].astype(str)
    final["long"] = df[long_col].astype(str)
    final["exclusions"] = df[excl_col].astype(str)

    return final


df = load_icd10()


# =========================================================
#  HANVION CSS UI
# =========================================================
st.markdown("""
<style>

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

.h-muted { color:#6b7280; }
.dark-mode .h-muted { color:#cbd5e1 !important; }

</style>
""", unsafe_allow_html=True)


# =========================================================
#  PERPLEXITY FUNCTION (FIXED MODEL)
# =========================================================
def ask_ai(prompt):
    api_key = st.secrets["PPLX_API_KEY"]

    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # FIXED: use valid Perplexity model
    payload = {
        "model": "sonar-medium-online",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        out = r.json()
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
        <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
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
#  SEARCH LOGIC
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
#  DISPLAY EACH RESULT
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

    # --- Clinical Explanation ---
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}", key=f"c-{row['code']}"):
            prompt = f"""
            Provide a detailed clinical explanation for ICD-10 code {row['code']}:

            {row['short']}
            {row['long']}

            Include:
            - Clinical meaning
            - Typical signs/symptoms
            - Why clinicians use this code
            - How it differs from nearby codes
            Not medical advice.
            """
            st.write(ask_ai(prompt))

    # --- Patient-friendly explanation ---
    with st.expander("Patient-friendly explanation"):
        if st.button(f"Explain simply: {row['code']}", key=f"p-{row['code']}"):
            prompt = f"""
            Explain ICD-10 code {row['code']} in simple language.

            Include:
            - What the condition means
            - Typical symptoms
            - When someone should seek help
            Not medical advice.
            """
            st.write(ask_ai(prompt))

    # --- Compare codes ---
    with st.expander("Compare with another ICD-10 code"):
        cmp_code = st.text_input(
            f"Enter another code to compare with {row['code']}",
            key=f"cmp-{row['code']}"
        )
        if cmp_code:
            prompt = f"""
            Compare ICD-10 code {row['code']} ({row['short']})
            with {cmp_code}.

            Include:
            - Differences
            - Severity
            - Body system
            - Usage context
            Educational only.
            """
            st.write(ask_ai(prompt))

    st.markdown("---")

