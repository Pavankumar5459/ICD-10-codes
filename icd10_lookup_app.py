import streamlit as st
import pandas as pd
import requests
import os

# -----------------------------------------------------------
#  CONFIG
# -----------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
)

# -----------------------------------------------------------
#  DARK / LIGHT MODE OVERRIDE
# -----------------------------------------------------------
st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background: var(--background-color);
}

:root {
    --primary: #004e92;
    --primary-dark: #002f5e;

    --bg-light: #f8fafc;
    --bg-dark: #0d1117;
}

@media (prefers-color-scheme: light) {
    :root {
        --background-color: var(--bg-light);
        --text-color: #1e293b;
    }
}

@media (prefers-color-scheme: dark) {
    :root {
        --background-color: var(--bg-dark);
        --text-color: #f8fafc;
    }

    .code-card {
        background: #161b22 !important;
        border-color: #30363d !important;
    }
}

/* HEADER */
.header {
    background: linear-gradient(90deg, #003f76, #0073c7);
    padding: 38px;
    border-radius: 14px;
    text-align: center;
    color: white;
    margin-bottom: 30px;
}

.code-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 22px;
    border: 1px solid #e5e7eb;
    margin-bottom: 14px;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------
#  LOAD DATA
# -----------------------------------------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long",
        "NF EXCL": "nf_excl"
    }, inplace=True)

    return df

df = load_icd10()

# -----------------------------------------------------------
#  PPLX CALL
# -----------------------------------------------------------
def get_ai_summary(prompt):
    api_key = st.secrets["PPLX_API_KEY"]
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "pplx-70b-online",
        "messages": [
            {"role": "system", "content": "You are a clinical ICD-10 educator. Keep responses short, structured, and educational only."},
            {"role": "user", "content": prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        if "error" in data:
            return f"AI Error: {data['error']}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI Error: {e}"


# -----------------------------------------------------------
#  HEADER
# -----------------------------------------------------------
st.markdown("""
<div class="header">
    <h1>Hanvion Health · ICD-10 Explorer</h1>
    <p>Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------
#  SEARCH BAR
# -----------------------------------------------------------
query = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

results_per_page = st.number_input("Results per page", 10, 50, 20)
page = st.number_input("Page", 1, 20000, 1)

# -----------------------------------------------------------
#  FILTER RESULTS
# -----------------------------------------------------------
if query.strip():
    filt = df[
        df["code"].str.contains(query, case=False, na=False) |
        df["short"].str.contains(query, case=False, na=False) |
        df["long"].str.contains(query, case=False, na=False)
    ]

    total = len(filt)

    start = (page - 1) * results_per_page
    end = start + results_per_page
    subset = filt.iloc[start:end]

    st.write(f"Showing {len(subset)} of {total} results.")

    # -----------------------------------------------------------
    #  DISPLAY RESULTS
    # -----------------------------------------------------------
    for _, row in subset.iterrows():
        with st.expander(f"{row['code']} — {row['short']}"):
            st.markdown(f"""
            ### {row['code']} — {row['short']}
            {row['long']}
            """)

            if row["nf_excl"]:
                st.markdown(f"**NF EXCL:** {row['nf_excl']}")

            # Clinical Explanation
            with st.expander("Clinical explanation (AI, educational only)"):
                btn = st.button(f"Explain clinically: {row['code']}", key=f"clin_{row['code']}")
                if btn:
                    prompt = f"Explain the ICD-10 code {row['code']} clinically. Description: {row['long']}"
                    out = get_ai_summary(prompt)
                    st.write(out)

            # Patient Explanation
            with st.expander("Patient explanation"):
                btn2 = st.button(f"Explain simply: {row['code']}", key=f"pat_{row['code']}")
                if btn2:
                    prompt = f"Explain the ICD-10 code {row['code']} in simple patient-friendly language. Description: {row['long']}"
                    out = get_ai_summary(prompt)
                    st.write(out)

else:
    st.info("Begin typing above to search ICD-10 codes.")
