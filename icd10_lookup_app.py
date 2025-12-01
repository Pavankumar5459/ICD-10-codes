import streamlit as st
import pandas as pd
import requests


# ======================================================
# Load ICD-10 Dataset
# ======================================================
@st.cache_data
def load_icd10():
    """
    Auto-detects ICD-10 dataset columns and cleans.
    Works with ANY CMS Excel file you upload.
    """
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")

    # Normalize columns
    df.columns = df.columns.str.lower()

    # Detect possible columns
    possible_code_cols = ["code", "icd10code", "icd10 code", "dx code", "diagnosiscode"]
    possible_desc_cols = ["description", "shortdescription", "short desc", "diagnosis"]
    possible_long_cols = ["longdescription", "long desc", "full description"]

    def pick(col_list):
        for c in col_list:
            if c in df.columns:
                return c
        return None

    code_col = pick(possible_code_cols)
    desc_col = pick(possible_desc_cols)
    long_col = pick(possible_long_cols)

    # Build final normalized dataset
    final = pd.DataFrame()
    final["code"] = df[code_col].astype(str).str.strip()
    final["description"] = df[desc_col].astype(str).str.strip()
    final["long_description"] = (
        df[long_col].astype(str).str.strip() if long_col else df[desc_col]
    )
    final["chapter"] = ""        # dataset doesn’t provide, leave blank
    final["category"] = ""

    return final


df = load_icd10()



# ======================================================
# Perplexity AI API
# ======================================================
def get_pplx_key():
    return st.secrets.get("PPLX_API_KEY", None)


def pplx_query(prompt):
    """
    Safe wrapper around Perplexity Sonar AI API.
    """

    api_key = get_pplx_key()
    if not api_key:
        return "⚠️ Perplexity API key missing."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-medium",   # fixed model
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a medical educator. You produce structured summaries ONLY. "
                    "Never provide medical advice or treatment. "
                    "Keep responses concise but high-quality."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)

        if res.status_code != 200:
            return f"AI error {res.status_code}: {res.text}"

        data = res.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI error: {str(e)}"



# ======================================================
# Hanvion Theme
# ======================================================
st.markdown(
    """
    <style>
    .hanv-card {
        background: #faf5ff;
        border: 1px solid #e9d8fd;
        padding: 24px;
        border-radius: 12px;
    }
    .muted {
        color: #4a5568;
        font-size: 13px;
    }
    h1, h2, h3 {
        user-select: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ======================================================
# App Header
# ======================================================
st.title("Hanvion Health · ICD-10 Explorer")
st.caption("Search ICD-10 codes, view clinical context, and generate AI explanations.")



# ======================================================
# Search Controls
# ======================================================
with st.container():
    query = st.text_input("Search by ICD-10 code or diagnosis")
    results_per_page = st.number_input("Results per page", 5, 100, 20)
    page = st.number_input("Page", 1, 99999, 1)


# ======================================================
# Do NOT show anything until user searches
# ======================================================
if not query:
    st.info("Start by searching for an ICD-10 code or diagnosis.")
    st.stop()



# ======================================================
# Filter dataset
# ======================================================
filtered = df[df["description"].str.contains(query, case=False, na=False) |
              df["code"].str.contains(query, case=False, na=False)]

if filtered.empty:
    st.warning("No matching ICD-10 codes found.")
    st.stop()



# ======================================================
# Pagination
# ======================================================
start = (page - 1) * results_per_page
end = start + results_per_page

subset = filtered.iloc[start:end]

st.write(f"Showing {len(subset)} of {len(filtered)} results")



# ======================================================
# Render Each ICD-10 Result Card
# ======================================================
for _, row in subset.iterrows():
    st.markdown("---")
    st.subheader(f"{row['code']} — {row['description']}")

    st.markdown(
        f"""
        <div class="hanv-card">
            <p class="muted">{row['long_description']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------ #
    # Clinical Explanation (AI)
    # ------------------------------ #
    with st.expander("Clinical explanation (for educational use only)"):
        if st.button(f"Generate clinical explanation for {row['code']}"):
            prompt = (
                f"Provide a structured CLINICAL PROFESSIONAL explanation for ICD-10 code "
                f"{row['code']} ({row['description']}). "
                f"Include: definition, underlying mechanisms, diagnostic considerations, "
                f"clinical relevance, epidemiology, risk factors. "
                f"Do NOT include treatment or medical advice."
            )
            out = pplx_query(prompt)
            st.write(out)

    # ------------------------------ #
    # Patient-Friendly Explanation (AI)
    # ------------------------------ #
    with st.expander("Patient-friendly explanation (educational only)"):
        if st.button(f"Generate patient summary for {row['code']}"):
            prompt = (
                f"Explain ICD-10 code {row['code']} ({row['description']}) "
                f"in simple, easy-to-understand non-technical language. "
                f"Describe what it means, typical symptoms, why doctors record it. "
                f"NO medical advice or treatment instructions."
            )
            out = pplx_query(prompt)
            st.write(out)

    # ------------------------------ #
    # Compare with Another ICD-10 Code
    # ------------------------------ #
    with st.expander("Compare with another ICD-10 code"):
        compare_code = st.text_input(f"Compare another code with {row['code']}")
        if st.button(f"Compare {row['code']}"):
            prompt = (
                f"Compare ICD-10 code {row['code']} ({row['description']}) "
                f"with ICD-10 code {compare_code}. "
                f"Explain differences in meaning, usage, and clinical category. "
                f"No advice."
            )
            out = pplx_query(prompt)
            st.write(out)


