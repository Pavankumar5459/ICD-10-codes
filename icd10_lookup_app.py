# ============================================================
# Hanvion Health – ICD-10 Explorer (Flexible + AI + Chatbot)
# Works even when dataset has missing columns
# ============================================================

import streamlit as st
import pandas as pd
import requests

# ============================
# AI CONFIG (Perplexity AI)
# ============================
PPLX_API_KEY = ""   # Add your key (optional)
USE_AI = PPLX_API_KEY != ""


# ============================
# Load ICD-10 Data (Flexible)
# ============================
@st.cache_data
def load_data():
    df = pd.read_csv("icd10_data.csv", dtype=str).fillna("")

    # Ensure required fields exist
    required = ["code", "description", "long_description", "chapter", "category"]
    for col in required:
        if col not in df.columns:
            df[col] = ""

    return df


# ============================
# Hanvion Theme
# ============================
def inject_css():
    st.markdown("""
    <style>
    .block-container { max-width: 1180px; padding-top: 1rem; }
    h1, h2, h3, h4 { font-weight: 700; user-select:none; }
    .icd-card {
        background: #faf5ff;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #e9d5ff;
        margin-bottom: 20px;
    }
    .code-badge {
        background:#6b21a8; 
        color:white;
        padding:4px 10px;
        border-radius:6px;
        font-size:12px;
        font-weight:600;
    }
    .muted { color:#6b7280; font-size:12px; }
    </style>
    """, unsafe_allow_html=True)


# ============================
# AI Explanation (Single Code)
# ============================
def ai_explain(code, description):
    if not USE_AI:
        return "AI explanation disabled. Add API key to enable."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-small-chat",
            "messages": [{
                "role": "user",
                "content": f"Explain ICD-10 code {code}: {description} in simple terms."
            }]
        }

        r = requests.post(url, json=payload, headers=headers, timeout=10)

        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"AI error {r.status_code}: unable to fetch explanation."

    except Exception:
        return "AI temporarily unavailable."


# ============================
# AI Chatbot
# ============================
def ai_chatbot(user_message):
    if not USE_AI:
        return "AI chatbot disabled (no API key added)."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sonar-small-chat",
            "messages": [{"role":"user","content": user_message}]
        }

        r = requests.post(url, json=payload, headers=headers, timeout=10)

        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]

        return f"AI error {r.status_code}"

    except Exception:
        return "AI unavailable."


# ============================
# Render ICD-10 Card
# ============================
def render_card(row):
    st.markdown(f"""
    <div class="icd-card">
        <div class="code-badge">{row['code']}</div>
        <h3>{row['description']}</h3>

        <p>{row['long_description']}</p>

        <p class="muted">
            Chapter: {row['chapter']} · Category: {row['category']}
        </p>

        <p class="muted">Use this code in EHR / analytics appropriately.</p>
    </div>
    """, unsafe_allow_html=True)


# ============================
# MAIN APP
# ============================
def main():
    inject_css()
    df = load_data()

    st.title("ICD-10 Lookup · Hanvion Health")
    st.caption("Fast medical code lookup with AI-powered learning")

    # ----- SEARCH -----
    st.sidebar.title("Search Filters")

    search = st.sidebar.text_input("Search by code or disease").upper()
    per_page = st.sidebar.slider("Results per page", 5, 50, 10)

    filtered = df.copy()
    if search:
        filtered = filtered[
            df["code"].str.contains(search)
            | df["description"].str.upper().str.contains(search)
        ]

    st.write(f"### Showing {len(filtered)} results")

    # Pagination
    page = st.number_input("Page", min_value=1, max_value=max(1, len(filtered)//per_page+1), value=1)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = filtered.iloc[start:end]

    for _, row in page_df.iterrows():
        render_card(row)

        # AI BUTTON
        if st.button(f"Learn about {row['code']} (AI)", key=row['code']):
            st.info(ai_explain(row['code'], row['description']))

        # RELATED CODES EXPANDER
        with st.expander("Related ICD-10 codes"):
            related = df[df["code"].str.startswith(row["code"][:3])]
            for _, rel in related.iterrows():
                st.write(f"**{rel['code']}** – {rel['description']}")

    # ------ AI CHATBOT ------
    st.subheader("Ask AI about any disease, symptom, or ICD-10 code")

    user_msg = st.text_input("Ask a question:")
    if user_msg:
        st.write(ai_chatbot(user_msg))


if __name__ == "__main__":
    main()
