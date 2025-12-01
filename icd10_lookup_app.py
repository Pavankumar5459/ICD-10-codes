import streamlit as st
import pandas as pd
import requests
from PIL import Image
import os

# =====================================================
#  PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide"
)

# =====================================================
#  Hanvion Premium UI Styles
# =====================================================
st.markdown("""
<style>

body, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
}

/* Remove Streamlit code blocks */
code, pre { display: none !important; }

/* Card Styling */
.icd-card {
    background: rgba(245,240,255,0.55);
    border: 1px solid #ede9fe;
    padding: 22px;
    border-radius: 14px;
    margin-top: 18px;
}

/* Muted text */
.muted {
    color: #6b7280;
    font-size: 14px;
}

/* Logo container */
.header-box {
    display:flex;
    align-items:center;
    gap:18px;
    margin-bottom:10px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
#  LOGO HANDLING (Feature D)
# =====================================================
def load_logo():
    try:
        logo = Image.open("assets/hanvion_logo.png")
        return logo
    except:
        return None


logo = load_logo()

# =====================================================
#  HEADER WITH LOGO
# =====================================================
col1, col2 = st.columns([1,8])

with col1:
    if logo:
        st.image(logo, width=120)
    else:
        st.write("")

with col2:
    st.title("Hanvion Health · ICD-10 Explorer")

st.write("Search ICD-10 codes, view clinical context, and generate summaries.")


# =====================================================
#  LOAD ANY ICD-10 DATASET AUTOMATICALLY
# =====================================================

@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx", dtype=str)
    df = df.fillna("")

    # Column map for flexible dataset compatibility
    col_map = {
        "code": ["code", "icd10", "ICD10", "icd_code", "Code"],
        "description": ["description", "desc", "Diagnosis", "Short Description"],
        "long_description": ["long_description", "Long Description", "Definition", "Full Description"],
        "chapter": ["chapter", "Chapter"],
        "category": ["category", "Category"]
    }

    def find_col(possible):
        for c in possible:
            if c in df.columns:
                return c
        return None

    code_col = find_col(col_map["code"])
    desc_col = find_col(col_map["description"])
    long_col = find_col(col_map["long_description"])
    chap_col = find_col(col_map["chapter"])
    cat_col = find_col(col_map["category"])

    final = pd.DataFrame()
    final["code"] = df[code_col].astype(str).str.strip()
    final["description"] = df[desc_col].astype(str).str.strip() if desc_col else ""
    final["long_description"] = df[long_col].astype(str).str.strip() if long_col else final["description"]
    final["chapter"] = df[chap_col].astype(str).str.strip() if chap_col else "N/A"
    final["category"] = df[cat_col].astype(str).str.strip() if cat_col else "N/A"

    return final

df = load_icd10()

# =====================================================
#  PERPLEXITY AI
# =====================================================
def pplx_key():
    try:
        return st.secrets["PPLX_API_KEY"]
    except:
        return None

def ask_ai(prompt, mode="clinical"):
    api_key = pplx_key()
    if not api_key:
        return "AI is not configured. Add PPLX_API_KEY in Streamlit Secrets."

    system_role = (
        "You are a medical educator. Provide structured clinical explanation only. No medical advice."
        if mode == "clinical"
        else
        "Explain condition in simple, friendly terms for general public. No medical advice."
    )

    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Request Failed: {e}"


# =====================================================
#  SEARCH UI
# =====================================================

query = st.text_input("Search by ICD code or diagnosis", "")
results_per_page = st.number_input("Results per page", 5, 100, 20)
page = st.number_input("Page", 1, 999, 1)

# Hide results until searching
if query.strip() == "":
    st.info("Begin typing to search ICD-10 codes…")
    st.stop()

mask = df.apply(lambda row: query.lower() in row.astype(str).str.lower().to_string(), axis=1)
results = df[mask]

# ================================  
#  FEATURE A — EXPORT SEARCH RESULTS  
# ================================
if len(results) > 0:
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download results as CSV",
        data=csv,
        file_name="icd10_search_results.csv",
        mime="text/csv"
    )

# PAGINATION
start = (page - 1) * results_per_page
end = start + results_per_page

st.caption(f"Showing {start+1}–{min(end,len(results))} of {len(results)} results.")
subset = results.iloc[start:end]


# =====================================================
#  DISPLAY ICD-10 CARDS
# =====================================================

for _, row in subset.iterrows():

    st.markdown("<div class='icd-card'>", unsafe_allow_html=True)
    st.subheader(f"{row['code']} — {row['description']}")
    st.write(row["long_description"])
    st.markdown(
        f"<p class='muted'>Chapter: {row['chapter']} · Category: {row['category']}</p>",
        unsafe_allow_html=True
    )

    # ---------- Clinical Expander ----------
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}", key=f"clin_{row['code']}"):
            prompt = f"Provide a structured clinical explanation for ICD-10 code {row['code']} ({row['description']})."
            st.write(ask_ai(prompt, mode="clinical"))

    # ---------- Patient Expander ----------
    with st.expander("Patient-friendly explanation"):
        if st.button(f"Explain simply: {row['code']}", key=f"pat_{row['code']}"):
            prompt = f"Explain ICD-10 {row['code']} ({row['description']}) in simple layperson language."
            st.write(ask_ai(prompt, mode="patient"))

    # ---------- Compare ----------
    with st.expander("Compare with another ICD-10 code"):
        compare_code = st.text_input(f"Enter ICD-10 code to compare with {row['code']}", key=f"cmp_{row['code']}")
        if st.button(f"Compare", key=f"cmp_btn_{row['code']}"):
            prompt = (
                f"Compare ICD-10 code {row['code']} ({row['description']}) "
                f"with ICD-10 code {compare_code}. Explain differences in classification only."
            )
            st.write(ask_ai(prompt, mode="clinical"))

    st.markdown("</div>", unsafe_allow_html=True)
