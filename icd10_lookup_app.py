import streamlit as st
import pandas as pd
import requests


# ==========================================================
# 1) LOAD ICD-10 DATA SAFELY FROM ANY CMS FILE
# ==========================================================
@st.cache_data
def load_icd10():
    """
    Loads ICD-10 Excel file and auto-detects code/description columns.
    Works with CMS files even when column names vary.
    """

    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.lower().str.strip()

    # ---- Identify code column ----
    code_candidates = ["code", "icd10 code", "icd10code", "diagnosiscode", "dx code"]
    code_col = next((c for c in df.columns if c in code_candidates), None)

    if not code_col:
        # fallback = first column
        code_col = df.columns[0]

    # ---- Identify short description ----
    short_candidates = ["short description", "short desc", "description", "desc"]
    short_col = next((c for c in df.columns if c in short_candidates), None)

    if not short_col:
        # fallback = second column or code column
        short_col = df.columns[1] if len(df.columns) > 1 else code_col

    # ---- Identify long description ----
    long_candidates = ["long description", "long desc", "full description"]
    long_col = next((c for c in df.columns if c in long_candidates), short_col)

    # ---- Build final dataset ----
    final = pd.DataFrame()
    final["code"] = df[code_col].astype(str).str.strip()
    final["description"] = df[short_col].astype(str).str.strip()
    final["long_description"] = df[long_col].astype(str).str.strip()

    # Optional metadata — your file may not have these
    final["chapter"] = ""
    final["category"] = ""

    # Remove blank codes
    final = final[final["code"] != ""].reset_index(drop=True)

    return final



df = load_icd10()



# ==========================================================
# 2) PERPLEXITY AI WRAPPER
# ==========================================================
def pplx_key():
    return st.secrets.get("PPLX_API_KEY", None)


def ask_ai(prompt):
    """Safe Perplexity sonar-medium request."""
    key = pplx_key()
    if not key:
        return "⚠️ AI not configured. Add PPLX_API_KEY in Streamlit Secrets."

    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-medium",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a medical educator. "
                    "Provide structured educational explanations ONLY. "
                    "No diagnosis, no treatment, no medical advice."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.25
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"

        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI request failed: {e}"



# ==========================================================
# 3) HANVION THEME
# ==========================================================
st.markdown(
    """
    <style>
    .card {
        background: #faf5ff;
        border: 1px solid #e9d8fd;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 18px;
    }
    .muted { font-size: 13px; color: #4a5568; }
    </style>
    """,
    unsafe_allow_html=True
)



# ==========================================================
# 4) APP UI
# ==========================================================
st.title("Hanvion Health · ICD-10 Explorer")
st.caption("Educational ICD-10 lookup with AI explanations (no clinical use).")


# -----------------------
# Search Bar
# -----------------------
query = st.text_input("Search ICD-10 code or condition")

if not query:
    st.info("Start typing to view ICD-10 results.")
    st.stop()

filtered = df[
    df["code"].str.contains(query, case=False, na=False)
    | df["description"].str.contains(query, case=False, na=False)
    | df["long_description"].str.contains(query, case=False, na=False)
]

if filtered.empty:
    st.warning("No matching ICD-10 codes found.")
    st.stop()

# Pagination
per_page = st.number_input("Results per page", 5, 50, 15)
page = st.number_input("Page", 1, 9999, 1)

start = (page - 1) * per_page
end = start + per_page

subset = filtered.iloc[start:end]

st.write(f"Showing {len(subset)} of {len(filtered)} results.")



# ==========================================================
# 5) RENDER EACH ICD CARD
# ==========================================================
for _, row in subset.iterrows():
    st.markdown("---")
    st.subheader(f"{row['code']} — {row['description']}")

    st.markdown(
        f"<div class='card'>{row['long_description']}</div>",
        unsafe_allow_html=True
    )

    # ---------- Clinical Explanation ----------
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}"):
            prompt = (
                f"Provide a high-quality CLINICAL explanation of ICD-10 {row['code']} "
                f"({row['description']}). Include: definition, clinical context, "
                f"key documentation points, relevant physiology, but NO treatment."
            )
            st.write(ask_ai(prompt))

    # ---------- Patient-Friendly ----------
    with st.expander("Patient-friendly explanation"):
        if st.button(f"Explain simply: {row['code']}"):
            prompt = (
                f"Explain ICD-10 {row['code']} ({row['description']}) "
                f"in simple language with NO clinical terms, NO medical advice."
            )
            st.write(ask_ai(prompt))

    # ---------- Compare Codes ----------
    with st.expander("Compare with another ICD-10 code"):
        other = st.text_input(f"Enter code to compare with {row['code']}")
        if st.button(f"Compare {row['code']} with {other}"):
            prompt = (
                f"Compare ICD-10 codes {row['code']} and {other}. "
                f"Explain conceptual differences, category differences, "
                f"and when each is typically used. NO treatment guidance."
            )
            st.write(ask_ai(prompt))
