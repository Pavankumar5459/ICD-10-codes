import streamlit as st
import pandas as pd
import requests
import os

# ------------------------------------------------------
#  Hanvion Health – ICD-10 Explorer (Final Version)
#  Using Perplexity pplx-70b-instruct + clean UI
# ------------------------------------------------------

st.set_page_config(
    page_title="Hanvion Health • ICD-10 Explorer",
    layout="wide"
)

# ----------------------------
#  LOAD DATASET
# ----------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    # Rename columns into a standard format
    col_map = {
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_desc",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_desc",
        "NF EXCL": "nf_excl"
    }
    df = df.rename(columns=col_map)

    df["short_desc"] = df["short_desc"].astype(str)
    df["long_desc"] = df["long_desc"].astype(str)
    df["nf_excl"] = df["nf_excl"].astype(str)

    return df[["code", "short_desc", "long_desc", "nf_excl"]]


df = load_icd10()

# ----------------------------------------------------------
#   PERPLEXITY AI — pplx-70b-instruct
# ----------------------------------------------------------
def ask_ai(prompt):
    api_key = st.secrets.get("PPLX_API_KEY", None)

    if not api_key:
        return None, "❗ Perplexity API key missing in Streamlit Secrets."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": "pplx-70b-instruct",   # ⭐ correct working model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"], None
        else:
            return None, f"AI Error: {data}"
    except Exception as e:
        return None, f"AI Error: {str(e)}"


# ----------------------------------------------------------
#  GLOBAL HANVION UI STYLE
# ----------------------------------------------------------
st.markdown("""
<style>

body {
    font-family: 'Segoe UI', sans-serif;
}

/* HEADER CARD */
.hanvion-header {
    padding: 45px;
    border-radius: 14px;
    background: linear-gradient(90deg, #003975, #0062AA);
    color: white;
    text-align: center;
    margin-bottom: 35px;
}

/* INPUT CLEAN LOOK */
.stTextInput>div>div>input {
    background-color: #F5F8FC;
    border-radius: 10px;
}

/* SECTION CARD */
.code-card {
    background: #F9F9FF;
    padding: 25px;
    border-radius: 16px;
    border: 1px solid #EEE;
    margin-top: 20px;
}

</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# HEADER
# ----------------------------------------------------------
st.markdown("""
<div class="hanvion-header">
    <h1>Hanvion Health • ICD-10 Explorer</h1>
    <p>Search validated CMS ICD-10 codes with optional AI explanations.</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# SEARCH BAR
# ----------------------------------------------------------
search = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 9999, 1)

# Optional feedback zone
if not search:
    st.info("Begin typing above to search ICD-10 codes.")
    st.stop()

# ----------------------------------------------------------
#  FILTER RESULTS
# ----------------------------------------------------------
search_lower = search.lower()

results = df[
    df["code"].str.lower().str.contains(search_lower) |
    df["short_desc"].str.lower().str.contains(search_lower) |
    df["long_desc"].str.lower().str.contains(search_lower)
]

total = len(results)
start = (page - 1) * per_page
end = start + per_page
paginated = results.iloc[start:end]

st.write(f"Showing {start+1}–{min(end, total)} of {total} results.")

# ----------------------------------------------------------
# DISPLAY MATCHING RESULTS
# ----------------------------------------------------------
for _, row in paginated.iterrows():
    st.markdown(f"""
    <div class='code-card'>
        <h3>{row['code']} — {row['short_desc']}</h3>
        <p>{row['long_desc']}</p>
        <p><b>NF EXCL:</b> {row['nf_excl']}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Clinical explanation (AI) ---
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}"):
            prompt = f"""
            Provide a clinical explanation for ICD-10 code {row['code']}:
            {row['short_desc']}
            {row['long_desc']}

            Include:
            • clinical meaning
            • key causes
            • typical symptoms
            • how clinicians evaluate
            • general management (educational only)
            """

            answer, err = ask_ai(prompt)
            if err:
                st.error(err)
            else:
                st.write(answer)

    # --- Patient friendly explanation ---
    with st.expander("Patient explanation"):
        if st.button(f"Explain simply: {row['code']}"):
            prompt = f"""
            Explain this ICD-10 code in simple language for patients:
            Code: {row['code']}
            {row['short_desc']}
            {row['long_desc']}

            Make it friendly and easy to understand.
            """

            answer, err = ask_ai(prompt)
            if err:
                st.error(err)
            else:
                st.write(answer)

    # --- Comparison ---
    with st.expander("Compare with another ICD-10 code"):
        compare_code = st.text_input(f"Enter comparison code for {row['code']}", key=f"cmp_{row['code']}")
        if compare_code:
            prompt = f"Compare ICD-10 codes {row['code']} and {compare_code} in detail."
            answer, err = ask_ai(prompt)
            if err:
                st.error(err)
            else:
                st.write(answer)

