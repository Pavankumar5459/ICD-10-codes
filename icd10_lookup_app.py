import streamlit as st
import pandas as pd
import requests

# -----------------------------------------------------------
# HENVION THEME
# -----------------------------------------------------------
st.set_page_config(page_title="Hanvion Health · ICD-10 Explorer", layout="wide")

st.markdown("""
<style>
    .big-title {font-size:38px; font-weight:800; color:#222;}
    .muted {color:#6c727f; font-size:14px;}
    .han-card {
        background:#faf7ff;
        border:1px solid #efe8ff;
        padding:22px;
        border-radius:12px;
        margin-top:20px;
    }
    .section-header {
        background:#f4edff;
        padding:12px 18px;
        border-radius:10px;
        font-size:17px;
        font-weight:600;
        margin-top:10px;
        border:1px solid #e4d8ff;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------
# LOAD DATASET SAFELY
# -----------------------------------------------------------
@st.cache_data
def load_icd10():
    file_name = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

    try:
        df = pd.read_excel(file_name, engine="openpyxl", dtype=str).fillna("")
    except Exception as e:
        st.error(f"❌ Could not load dataset. Error:\n\n{e}")
        st.stop()

    rename_map = {
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_description",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_description",
        "NF EXCL": "nf_excl",
    }

    df = df.rename(columns=rename_map)

    for col in ["code", "short_description", "long_description", "nf_excl"]:
        if col not in df.columns:
            df[col] = ""

    return df


df = load_icd10()


# -----------------------------------------------------------
# PERPLEXITY AI FUNCTION
# -----------------------------------------------------------
PPLX_KEY = st.secrets.get("PPLX_API_KEY", "")

def perplexity_query(prompt):
    if not PPLX_KEY:
        return "⚠️ AI is not configured. Add PPLX_API_KEY in Streamlit secrets."

    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4
    }

    try:
        r = requests.post(url, json=payload, headers={
            "Authorization": f"Bearer {PPLX_KEY}",
            "Content-Type": "application/json"
        })
        data = r.json()

        return data.get("choices", [{}])[0].get("message", {}).get("content", "No response.")

    except Exception as e:
        return f"AI error: {e}"


# -----------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------
st.markdown("<div class='big-title'>Hanvion Health · ICD-10 Explorer</div>", unsafe_allow_html=True)
st.markdown("<p class='muted'>Search ICD-10 codes using the official CMS dataset. Educational explanations only.</p>", unsafe_allow_html=True)

st.write("")


# -----------------------------------------------------------
# SEARCH BAR
# -----------------------------------------------------------
query = st.text_input("Search ICD-10 code or diagnosis", placeholder="Example: asthma, E11, fracture")

results_per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 999, 1)


# -----------------------------------------------------------
# FILTER RESULTS
# -----------------------------------------------------------
if query.strip():
    q = query.lower()
    filtered = df[
        df["code"].str.lower().str.contains(q) |
        df["short_description"].str.lower().str.contains(q) |
        df["long_description"].str.lower().str.contains(q)
    ]
else:
    filtered = pd.DataFrame()   # show nothing until search


# -----------------------------------------------------------
# SHOW RESULTS
# -----------------------------------------------------------
if filtered.empty and query:
    st.warning("No matching codes found.")

elif not filtered.empty:

    total = len(filtered)
    start = (page - 1) * results_per_page
    end = start + results_per_page

    st.write(f"Showing {start+1}–{min(end, total)} of {total} results.")

    display_df = filtered.iloc[start:end]

    for _, row in display_df.iterrows():

        st.markdown(
            f"<div class='han-card'><h3>{row['code']} — {row['short_description']}</h3>",
            unsafe_allow_html=True
        )

        st.write(row["long_description"])

        st.markdown(
            f"<p class='muted'>NF EXCL: {row['nf_excl']}</p>",
            unsafe_allow_html=True
        )

        # --------------------------
        # CLINICAL EXPLANATION
        # --------------------------
        with st.expander("Clinical explanation (educational only)"):
            if st.button(f"Explain clinically: {row['code']}", key=f"clin_{row['code']}"):
                prompt = (
                    f"Explain ICD-10 code {row['code']} clinically. "
                    f"Condition: {row['short_description']}. "
                    f"Details: {row['long_description']}. "
                    f"Include pathophysiology, clinical features, and typical management. "
                    f"Educational only."
                )
                st.write(perplexity_query(prompt))

        # --------------------------
        # PATIENT SUMMARY
        # --------------------------
        with st.expander("Patient-friendly explanation"):
            if st.button(f"Explain simply: {row['code']}", key=f"simple_{row['code']}"):
                prompt = (
                    f"Explain ICD-10 code {row['code']} in very simple, easy-to-understand language. "
                    f"Condition: {row['short_description']}. "
                    f"Do NOT include medical jargon. Educational only."
                )
                st.write(perplexity_query(prompt))

        # --------------------------
        # COMPARE WITH ANOTHER CODE
        # --------------------------
        with st.expander("Compare with another ICD-10 code"):
            compare_code = st.text_input(
                f"Enter another code to compare with {row['code']}",
                key=f"cmp_{row['code']}"
            )
            if st.button(f"Compare with {row['code']}", key=f"cmpbtn_{row['code']}"):
                prompt = (
                    f"Compare ICD-10 code {row['code']} ({row['short_description']}) "
                    f"with code {compare_code}. Highlight differences in severity, cause, and usage."
                )
                st.write(perplexity_query(prompt))

        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")


