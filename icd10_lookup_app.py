import streamlit as st
import pandas as pd
import requests

# ---------------------------------------------------
# 1. PAGE CONFIG (Hanvion UI v2)
# ---------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health • ICD-10 Explorer",
    layout="wide"
)

# ---------------------------------------------------
# 2. CSS — Premium Hanvion UI
# ---------------------------------------------------
st.markdown("""
<style>

body {
    background-color: #f7f9fc !important;
}

/* Blue header */
.hanvion-header {
    background: linear-gradient(90deg, #003f73, #005fa3);
    padding: 45px;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 35px;
}
.hanvion-header h1 {
    color: white;
    font-size: 38px;
    font-weight: 700;
}
.hanvion-header p {
    color: #d8e7f7;
    font-size: 17px;
}

/* Expanded ICD-10 card */
.code-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0px 3px 10px rgba(0,0,0,0.06);
    margin-top: 15px;
}

/* Title inside card */
.code-title {
    font-size: 22px;
    font-weight: 700;
    color: #1a2a3a;
}

/* Subtext muted */
.muted {
    color: #6b7280;
    font-size: 14px;
}

/* Buttons */
.btn {
    background: #005fa3;
    padding: 8px 14px;
    color: white;
    border-radius: 8px;
    border: none;
}
.btn:hover {
    background: #004c82;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# 3. Perplexity Function
# ---------------------------------------------------
PPLX_API_KEY = st.secrets.get("PPLX_API_KEY", None)

def perplexity_explain(prompt):
    if not PPLX_API_KEY:
        return "⚠ Perplexity API key missing in Streamlit Secrets."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "pplx-70b-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300
    }

    try:
        r = requests.post(url, headers=headers, json=data, timeout=20)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Error: {str(e)}"


# ---------------------------------------------------
# 4. Load Dataset
# ---------------------------------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx", dtype=str)
    df = df.fillna("")
    df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long",
        "NF EXCL": "nfexcl"
    }, inplace=True)
    return df

df = load_icd10()


# ---------------------------------------------------
# 5. HEADER
# ---------------------------------------------------
st.markdown("""
<div class="hanvion-header">
    <h1>Hanvion Health • ICD-10 Explorer</h1>
    <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# 6. SEARCH BAR
# ---------------------------------------------------
search_term = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 500000, 1)


# ---------------------------------------------------
# 7. FILTER RESULTS
# ---------------------------------------------------
if search_term.strip():
    filtered = df[
        df["code"].str.contains(search_term, case=False, na=False) |
        df["short"].str.contains(search_term, case=False, na=False) |
        df["long"].str.contains(search_term, case=False, na=False)
    ]

    start = (page - 1) * per_page
    end = start + per_page
    current = filtered.iloc[start:end]

    st.write(f"Showing {len(current)} of {len(filtered)} results")

    # ---------------------------------------------------
    # 8. RENDER RESULTS — CLICK TO EXPAND CARD
    # ---------------------------------------------------
    for idx, row in current.iterrows():
        code = row["code"]
        title = row["short"]
        longd = row["long"]
        nfexcl = row["nfexcl"]

        with st.expander(f"{code} — {title}", expanded=False):
            st.markdown(f"""
            <div class="code-card">
                <div class="code-title">{code} — {title}</div>
                <p>{longd}</p>
                <p class="muted"><b>NF EXCL:</b> {nfexcl}</p>
            </div>
            """, unsafe_allow_html=True)

            # AI SECTION
            with st.spinner("AI generating clinical explanation…"):
                clinical = perplexity_explain(
                    f"Explain the clinical meaning, common presentation, risks, and management overview for ICD-10 code {code}: {title}. Keep structured."
                )
            st.subheader("Clinical explanation (AI, educational only)")
            st.write(clinical)

            with st.spinner("AI generating patient explanation…"):
                patient = perplexity_explain(
                    f"Explain the diagnosis {title} (ICD-10 {code}) in simple patient-friendly language."
                )
            st.subheader("Patient explanation")
            st.write(patient)

else:
    st.info("Begin typing above to search ICD-10 codes.")
