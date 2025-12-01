# ============================================================
# Hanvion Health – ICD-10 Explorer (Final Stable Version)
# Works perfectly with:
#  section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx
# ============================================================

import streamlit as st
import pandas as pd
import requests
import re


# ============================================================
# OPTIONAL AI CONFIG
# ============================================================
PPLX_API_KEY = ""   # Add your Perplexity API key here (optional)
USE_AI = PPLX_API_KEY != ""


# ============================================================
# LOAD ICD-10 DATA (WORKS EVEN WITH MISSING COLUMNS)
# ============================================================
@st.cache_data
def load_icd10():

    file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

    try:
        df = pd.read_excel(file_path, dtype=str).fillna("")
    except Exception as e:
        st.error(f"Failed to load ICD data: {e}")
        st.stop()

    # ------------------------------
    # Detect columns intelligently
    # ------------------------------
    cols = {c.lower(): c for c in df.columns}  # normalize lookup

    def pick(*names):
        """Return first matching column or ''."""
        for name in names:
            if name.lower() in cols:
                return cols[name.lower()]
        return None

    # Try to match typical ICD-10 column names
    code_col = pick("code", "icd_code", "icd10", "dxcode")
    short_col = pick("short description", "short_desc", "description", "dx_name")
    long_col = pick("long description", "long_desc", "full_description")
    chapter_col = pick("chapter", "icd10 chapter")
    category_col = pick("category", "group")

    # Build final normalized dataframe
    df_final = pd.DataFrame()
    df_final["code"] = df[code_col].astype(str).str.strip() if code_col else ""

    df_final["description"] = (
        df[short_col].astype(str).str.strip() if short_col else ""
    )

    df_final["long_description"] = (
        df[long_col].astype(str).str.strip() if long_col else ""
    )

    df_final["chapter"] = (
        df[chapter_col].astype(str).str.strip() if chapter_col else ""
    )

    # If category missing → derive automatically (first 3 characters)
    if category_col:
        df_final["category"] = df[category_col].astype(str).str.strip()
    else:
        df_final["category"] = df_final["code"].str.extract(r"^([A-Z]\\d{2})", expand=False).fillna("")

    # Drop empty codes
    df_final = df_final[df_final["code"] != ""].reset_index(drop=True)

    return df_final


# ============================================================
# HANVION THEME
# ============================================================
def inject_css():
    st.markdown("""
    <style>

    .block-container {
        max-width: 1180px;
        padding-top: 1rem;
    }

    h1, h2, h3, h4 { 
        user-select: none;
        font-weight:700;
    }

    .icd-card {
        background: #faf5ff;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #e9d5ff;
        margin-bottom: 22px;
    }

    .code-badge {
        background:#6b21a8;
        color:white;
        padding:4px 10px;
        border-radius:6px;
        font-size:12px;
        font-weight:600;
    }

    .muted { 
        color:#6b7280; 
        font-size:12px;
    }

    </style>
    """, unsafe_allow_html=True)


# ============================================================
# AI EXPLANATION
# ============================================================
def ai_explain(code, description):

    if not USE_AI:
        return "AI is disabled. Add PPLX_API_KEY to enable explanations."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}",
                   "Content-Type": "application/json"}

        payload = {
            "model": "sonar-small-chat",
            "messages": [{
                "role": "user",
                "content": f"Explain ICD-10 code {code}: {description} in simple terms."
            }]
        }

        r = requests.post(url, json=payload, headers=headers, timeout=12)

        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]

        return f"AI error {r.status_code}"

    except Exception:
        return "AI unavailable."


# ============================================================
# AI CHATBOT
# ============================================================
def ai_chat(message):
    if not USE_AI:
        return "AI chatbot disabled (no API key)."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-small-chat",
            "messages": [{"role": "user", "content": message}]
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()["choices"][0]["message"]["content"]

    except Exception:
        return "AI unavailable."


# ============================================================
# RENDER ICD CARD
# ============================================================
def render_card(row):
    st.markdown(f"""
    <div class="icd-card">

        <div class="code-badge">{row['code']}</div>

        <h3>{row['description']}</h3>

        <p style="font-size:14px;">{row['long_description']}</p>

        <p class="muted">
            Chapter: {row['chapter']} · Category: {row['category']}
        </p>

    </div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN APP
# ============================================================
def main():

    inject_css()
    df = load_icd10()

    st.title("ICD-10 Lookup · Hanvion Health")
    st.caption("Search ICD-10 codes, view descriptions, and use AI explanations.")

    # --------------------------
    # Search Bar
    # --------------------------
    search = st.text_input("Search by code or keyword").upper()

    filtered = df.copy()
    if search:
        filtered = filtered[
            df["code"].str.contains(search)
            | df["description"].str.upper().str.contains(search)
            | df["long_description"].str.upper().str.contains(search)
        ]

    st.write(f"### {len(filtered)} matching results")

    # --------------------------
    # Display Cards
    # --------------------------
    for _, row in filtered.iterrows():
        render_card(row)

        # AI Explanation Button
        if st.button(f"AI explanation for {row['code']}", key=row['code']):
            st.info(ai_explain(row["code"], row["description"]))

        # Related Codes
        with st.expander("Related ICD-10 codes"):
            related = df[df["code"].str.startswith(row["code"][:3])]
            for _, r in related.iterrows():
                st.write(f"**{r['code']}** – {r['description']}")

    # --------------------------
    # AI CHATBOT
    # --------------------------
    st.subheader("Ask AI Anything")
    user_msg = st.text_input("Ask medical questions or ICD-10 questions:")

    if user_msg:
        st.write(ai_chat(user_msg))


# Run app
if __name__ == "__main__":
    main()
