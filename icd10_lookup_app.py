import streamlit as st
import pandas as pd
import requests
import os

# ------------------------------------------------------------
# Load ICD-10 Dataset
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    # Normalize columns so the app can work with ANY dataset format
    df.columns = [c.lower().strip() for c in df.columns]

    # Auto-detect best-matching columns
    possible_cols = {
        "code": ["code", "icd10", "icd_10_code", "icd code"],
        "description": ["description", "short description", "desc"],
        "long_description": ["long description", "full description", "details"],
        "chapter": ["chapter", "chap", "icd chapter"],
        "category": ["category", "diagnosis group", "dx category"]
    }

    colmap = {}
    for key, patterns in possible_cols.items():
        for p in patterns:
            matches = [c for c in df.columns if p in c]
            if matches:
                colmap[key] = matches[0]
                break

    # If missing fields → create blanks
    for k in ["long_description", "chapter", "category"]:
        if k not in colmap:
            df[k] = ""
            colmap[k] = k

    return df, colmap


# ------------------------------------------------------------
# Perplexity AI Function
# ------------------------------------------------------------
def ask_perplexity(prompt):
    api_key = os.environ.get("PPLX_API_KEY")

    if not api_key:
        return "**AI unavailable — no API key configured.**"

    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "pplx-70b-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 230,
        "temperature": 0.4,
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        data = r.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return "AI error — no valid response."

    except Exception as e:
        return f"AI error: {e}"


# ------------------------------------------------------------
# Hanvion Theme Styles
# ------------------------------------------------------------
def inject_css():
    st.markdown("""
        <style>
        .hanvion-card {
            background:#faf7ff;
            padding:22px;
            border-radius:14px;
            border:1px solid #ece7ff;
        }
        .muted { color:#666; font-size:13px; }
        .code-pill {
            background:#6b46c1;
            color:white;
            padding:4px 12px;
            border-radius:6px;
            font-weight:600;
            font-size:13px;
        }
        </style>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------
# UI Component — Display a Single ICD Record
# ------------------------------------------------------------
def render_record(row):
    inject_css()

    st.markdown(f"<div class='code-pill'>{row['code']}</div>", unsafe_allow_html=True)

    st.markdown(f"### {row['description']}")
    st.write(row["long_description"])

    st.markdown(
        f"<p class='muted'>Chapter: {row['chapter']} · Category: {row['category']}</p>",
        unsafe_allow_html=True
    )

    with st.expander("Clinical explanation (educational only)"):
        st.write(
            f"This condition (**{row['description']}**) typically refers to: "
            f"{row['long_description'] or 'No extended information available.'}"
        )

    with st.expander("Patient-friendly summary"):
        st.write(
            f"**In simple words:** {row['description']}. "
            "This is an educational summary, not medical advice."
        )

    # ---------------------------
    # AI CHATBOT SECTION
    # ---------------------------
    with st.expander("Ask AI about this condition"):
        st.caption("Educational purposes only. Not medical advice.")

        user_q = st.text_input(
            f"Your question about code {row['code']}",
            placeholder="Example: What causes this? How is it treated?"
        )

        if user_q:
            with st.spinner("AI is thinking..."):
                prompt = (
                    f"You are a medical educator. Explain the condition related "
                    f"to ICD-10 code {row['code']} ({row['description']}). "
                    f"User question: {user_q}. Provide a clear, factual, non-medical "
                    f"educational explanation (no diagnosis or treatment advice)."
                )
                ai_answer = ask_perplexity(prompt)

            st.write(ai_answer)


# ------------------------------------------------------------
# MAIN APP
# ------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Hanvion Health • ICD-10 Explorer",
        layout="wide"
    )

    st.title("Hanvion Health · ICD-10 Explorer")
    st.caption("Search ICD-10 codes, view clinical context, and learn using AI (optional).")

    df, col = load_data()

    query = st.text_input(
        "Search by ICD code or diagnosis",
        placeholder="Example: E11, asthma, cholera"
    )

    per_page = st.number_input("Results per page", 5, 50, 20)
    page = st.number_input("Page", 1, 99999, 1)

    # -----------------------------
    # No results shown until user searches
    # -----------------------------
    if not query.strip():
        st.info("Start typing above to search ICD-10 codes.")
        return

    q = query.lower().strip()

    results = df[
        df[col["code"]].str.contains(q, case=False) |
        df[col["description"]].str.contains(q, case=False) |
        df[col["long_description"]].str.contains(q, case=False)
    ]

    total = len(results)
    st.caption(f"Showing results for **{query}** — {total} matches found.")

    if total == 0:
        st.warning("No matching ICD-10 codes found.")
        return

    start = (page - 1) * per_page
    end = start + per_page
    page_results = results.iloc[start:end]

    for _, row in page_results.iterrows():
        st.markdown("<div class='hanvion-card'>", unsafe_allow_html=True)
        render_record({
            "code": row[col["code"]],
            "description": row[col["description"]],
            "long_description": row.get(col.get("long_description"), ""),
            "chapter": row.get(col.get("chapter"), "N/A"),
            "category": row.get(col.get("category"), "N/A"),
        })
        st.markdown("</div><br>", unsafe_allow_html=True)


# ------------------------------------------------------------
# Run App
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
