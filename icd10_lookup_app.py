import streamlit as st
import pandas as pd
import requests

# =========================================================
#  Hanvion ICD-10 Explorer (Perplexity FIXED MODEL)
# =========================================================

st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
    page_icon="💠",
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

    out = pd.DataFrame()
    out["code"] = df["code"]
    out["short"] = df["short_description_valid_icd-10_fy2025"]
    out["long"] = df["long_description_valid_icd-10_fy2025"]
    out["exclusions"] = df["nf_excl"]

    return out

df = load_icd10()


# =========================================================
#  PERPLEXITY AI (WORKING MODEL)
# =========================================================
def ask_ai(prompt):
    api_key = st.secrets["PPLX_API_KEY"]

    url = "https://api.perplexity.ai/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": "pplx-70b-online",  # <<< VALID MODEL
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return f"AI Error: {data}"
    except Exception as e:
        return f"AI Error: {str(e)}"


# =========================================================
#  HEADER UI
# =========================================================
st.markdown("""
<style>
.h-banner {
    background: linear-gradient(90deg,#004c97,#0073cf);
    padding:40px;
    border-radius:18px;
    text-align:center;
    color:white;
    margin:25px 0 35px 0;
}
.result-card {
    background:white;
    border-radius:14px;
    border:1px solid #e5e7eb;
    padding:20px;
    margin-bottom:20px;
}
.h-muted { color:#6b7280; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="h-banner">
    <h1>Hanvion Health · ICD-10 Explorer</h1>
    <p>Search ICD-10 codes with official CMS data and AI explanations.</p>
</div>
""", unsafe_allow_html=True)


# =========================================================
#  SEARCH BAR
# =========================================================
query = st.text_input("Search ICD-10 code or diagnosis", placeholder="Example: J45, asthma, diabetes…")

results_per_page = st.number_input("Results per page", 5, 100, 20)
page = st.number_input("Page", 1, 999999, 1)


# =========================================================
#  SEARCH LOGIC
# =========================================================
if not query.strip():
    st.info("Start typing to search ICD-10 codes.")
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

subset = filtered.iloc[start:end]

st.write(f"Showing **{start+1}–{min(end,total)}** of **{total}** results.")


# =========================================================
#  DISPLAY RESULTS
# =========================================================
for _, row in subset.iterrows():

    # CARD
    st.markdown(
        f"""
        <div class="result-card">
            <h3>{row['code']} — {row['short']}</h3>
            <p class='h-muted'>{row['long']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Clinical explanation
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}", key=f"clin-{row['code']}"):
            prompt = f"""
            Provide a detailed clinical explanation for ICD-10 code {row['code']}:

            {row['short']}
            {row['long']}

            Include:
            - Clinical meaning
            - Typical symptoms
            - Common causes
            - Coding considerations
            Educational only.
            """
            st.write(ask_ai(prompt))

    # Patient-friendly explanation
    with st.expander("Patient explanation"):
        if st.button(f"Explain simply: {row['code']}", key=f"pat-{row['code']}"):
            prompt = f"""
            Explain ICD-10 code {row['code']} ({row['short']}) in simple terms for patients.

            Include:
            - What it means
            - Common symptoms
            - When to seek help
            Not medical advice.
            """
            st.write(ask_ai(prompt))

    # Compare with another code
    with st.expander("Compare with another ICD-10 code"):
        other = st.text_input(f"Enter second code to compare with {row['code']}", key=f"cmp-{row['code']}")
        if other:
            prompt = f"""
            Compare ICD-10 code {row['code']} ({row['short']})
            with {other}.

            Provide:
            - Differences
            - Severity
            - What each represents
            - Why they're coded separately
            """
            st.write(ask_ai(prompt))

    st.markdown("---")
