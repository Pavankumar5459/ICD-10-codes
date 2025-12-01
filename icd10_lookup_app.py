import streamlit as st
import pandas as pd
import requests

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide"
)

# ============================================================
# CUSTOM THEME (LAVENDER HANVION UI FROM THE VERSION YOU LIKED)
# ============================================================
st.markdown("""
<style>
/* Overall page */
body {
    background-color: #ffffff;
}

/* Title */
.hanvion-title {
    font-size: 36px;
    font-weight: 900;
    color: #1d1d1d;
    margin-bottom: 10px;
}

/* Card container */
.icd-card {
    background: #f8f2ff;
    border: 1px solid #e8d9ff;
    padding: 22px;
    border-radius: 14px;
    margin-top: 25px;
}

/* Code badge */
.code-badge {
    background: #7b2ff7;
    padding: 6px 14px;
    border-radius: 12px;
    font-size: 13px;
    color: white;
    display: inline-block;
    margin-bottom: 10px;
}

/* Section header */
.section-header {
    font-size: 20px;
    font-weight: 700;
    margin-top: 25px;
}

/* Subcards */
.subcard {
    background: #ffffff;
    border: 1px solid #ebe5f7;
    padding: 15px;
    border-radius: 10px;
    margin-top: 10px;
}

/* Muted text */
.muted {
    color: #666;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD CMS EXCEL DATASET
# ============================================================
@st.cache_data
def load_cms_excel():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")
    
    df.columns = df.columns.str.strip().str.upper()
    
    # Standardize mapping
    df_final = pd.DataFrame({
        "code": df["CODE"],
        "description": df["SHORT DESCRIPTION (VALID ICD-10 FY2025)"],
        "long_description": df["LONG DESCRIPTION (VALID ICD-10 FY2025)"],
        "nf_excl": df["NF EXCL"]
    })
    return df_final

df = load_cms_excel()

# ============================================================
# SEARCH BAR
# ============================================================
st.markdown('<div class="hanvion-title">Hanvion Health · ICD-10 Explorer</div>', unsafe_allow_html=True)
st.write("Search ICD-10 codes using the official CMS dataset. Educational explanations only.")

query = st.text_input("Search ICD-10 code or diagnosis", placeholder="Example: E11, diabetes, asthma, fracture")

results_per_page = st.number_input("Results per page", value=20, step=1)
page = st.number_input("Page", min_value=1, value=1, step=1)

# Perform search
results = df[df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)] if query else pd.DataFrame()

# Pagination
total_results = len(results)
start = (page - 1) * results_per_page
end = start + results_per_page
page_results = results.iloc[start:end] if total_results > 0 else []

# ============================================================
# AI: PERPLEXITY
# ============================================================
def perplexity_generate(prompt, api_key):
    if not api_key:
        return "AI unavailable — please enter API key."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    payload = {
        "model": "pplx-7b-online",  # BEST WORKING MODEL
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Request failed: {e}"

# User's API key
api_key = st.text_input("Perplexity API key (optional)", type="password")

# ============================================================
# SHOW RESULTS
# ============================================================
if query and total_results == 0:
    st.warning("No matching ICD-10 codes found.")

if query and total_results > 0:
    st.write(f"Showing {start+1}–{min(end,total_results)} of {total_results} results.")

    for _, row in page_results.iterrows():
        code = row["code"]
        desc = row["description"]
        long_desc = row["long_description"]
        nf = row["nf_excl"]

        st.markdown(f"""
        <div class="icd-card">
            <div class="code-badge">{code}</div>
            <h3>{desc}</h3>
            <p class="muted">{long_desc}</p>
        """, unsafe_allow_html=True)

        # NF EXCL
        if nf.strip():
            with st.expander("Excluded conditions (NF EXCL)"):
                st.write(nf)

        # Clinical Explanation
        with st.expander("Clinical explanation (educational only)"):
            clinical_btn = st.button(f"Explain clinically: {code}", key=f"clin-{code}")
            if clinical_btn:
                prompt = f"Provide a clinical explanation for ICD-10 code {code}: {desc}. No emojis."
                st.write(perplexity_generate(prompt, api_key))

        # Patient-friendly
        with st.expander("Patient-friendly explanation"):
            patient_btn = st.button(f"Explain simply: {code}", key=f"pat-{code}")
            if patient_btn:
                prompt = f"Explain ICD-10 code {code} ({desc}) in simple language for patients. No emojis."
                st.write(perplexity_generate(prompt, api_key))

        # Compare code
        with st.expander("Compare with another ICD-10 code"):
            compare_code = st.text_input(f"Enter another ICD-10 code to compare with {code}", key=f"cmp-{code}")
            compare_btn = st.button(f"Compare {code} with {compare_code}", key=f"cmpbtn-{code}")
            if compare_btn:
                prompt = f"Compare ICD-10 codes {code} and {compare_code}. Explain differences. No emojis."
                st.write(perplexity_generate(prompt, api_key))

        st.markdown("</div>", unsafe_allow_html=True)
