# =========================================================
# Hanvion Health – Advanced ICD-10 Explorer + AI (Perplexity)
# =========================================================

import streamlit as st
import pandas as pd
import requests

ICD_XLSX = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"


# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="Hanvion Health | ICD-10 Explorer",
    page_icon="🩺",
    layout="wide",
)


# ---------------------------
# HANVION THEME (RED PREMIUM)
# ---------------------------
HANVION_CSS = """
<style>

body, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
}

/* Main width */
.block-container {
    max-width: 1100px !important;
}

/* Header Gradient */
.hanvion-header {
    background: linear-gradient(90deg, #8A0E1C, #B3122F, #8A0E1C);
    padding: 24px 26px;
    border-radius: 14px;
    margin-bottom: 20px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.23);
}
.hanvion-header-title {
    color: #ffffff;
    font-weight: 800;
    font-size: 28px;
    margin: 0;
}
.hanvion-header-subtitle {
    color: #ffd6d6;
    font-size: 14px;
    margin-top: 6px;
}

/* Cards */
.hanvion-card {
    background: #ffffff;
    padding: 18px 18px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 14px rgba(15,23,42,0.06);
    margin-bottom: 14px;
}

/* Code title inside card */
.hanvion-code {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
}
.hanvion-desc {
    font-size: 14px;
    color: #4b5563;
    margin-top: 4px;
}
.hanvion-tags {
    font-size: 12px;
    color: #6b7280;
    margin-top: 6px;
}

/* Copy button */
.hanvion-copy-btn {
    margin-top: 8px;
    padding: 5px 12px;
    background: #1d4ed8;
    color: #ffffff;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 12px;
}
.hanvion-copy-btn:hover {
    background: #1e40af;
}

/* Prevent selecting headings */
.noselect, h1, h2, h3, h4 {
    user-select: none;
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
    .hanvion-card {
        background: #111827;
        border: 1px solid #374151;
    }
    .hanvion-code {
        color: #e5e7eb;
    }
    .hanvion-desc {
        color: #d1d5db;
    }
    .hanvion-tags {
        color: #9ca3af;
    }
    .hanvion-header {
        background: linear-gradient(90deg, #5b0b13, #891025, #5b0b13);
    }
}
</style>
"""
st.markdown(HANVION_CSS, unsafe_allow_html=True)


# ---------------------------
# CHAPTER MAPPING
# ---------------------------
def map_chapter(letter: str) -> str:
    if not isinstance(letter, str) or not letter:
        return "Unknown"
    l = letter.upper()

    mapping = {
        "A": "Infectious & Parasitic Diseases",
        "B": "Infectious & Parasitic Diseases",
        "C": "Neoplasms",
        "D": "Blood Disorders / Neoplasms",
        "E": "Endocrine & Metabolic",
        "F": "Mental & Behavioural Disorders",
        "G": "Nervous System",
        "H": "Eye / Ear Disorders",
        "I": "Cardiovascular (Heart & Vessels)",
        "J": "Respiratory System",
        "K": "Digestive System",
        "L": "Skin & Subcutaneous Tissue",
        "M": "Musculoskeletal System",
        "N": "Genitourinary System",
        "O": "Pregnancy, Childbirth & Puerperium",
        "P": "Perinatal Conditions",
        "Q": "Congenital Malformations",
        "R": "Symptoms, Signs & Abnormal Findings",
        "S": "Injury, Poisoning & Certain Other Consequences",
        "T": "Injury, Poisoning & Certain Other Consequences",
        "V": "External Causes of Morbidity",
        "W": "External Causes of Morbidity",
        "X": "External Causes of Morbidity",
        "Y": "External Causes of Morbidity",
        "Z": "Factors Influencing Health Status",
    }
    return mapping.get(l, "Unmapped Chapter")


# ---------------------------
# LOAD + PREPROCESS ICD-10
# ---------------------------
@st.cache_data(show_spinner="Loading ICD-10 codes…")
def load_icd10():
    df = pd.read_excel(ICD_XLSX, dtype=str)

    # Clean columns
    df.columns = [c.strip() for c in df.columns]

    # Try to auto-detect code + description columns
    code_candidates = ["ICD10", "ICD10CODE", "ICD-10 Code", "Code", "DIAG_CD"]
    desc_candidates = ["Description", "LONG_DESCRIPTION", "LONG_DESC", "ICD10DESCRIPTION"]

    code_col = None
    desc_col = None

    for c in df.columns:
        c_upper = c.replace(" ", "").upper()
        if c_upper in [x.upper() for x in code_candidates] and code_col is None:
            code_col = c
        if c_upper in [x.upper() for x in desc_candidates] and desc_col is None:
            desc_col = c

    if code_col is None:
        code_col = df.columns[0]
    if desc_col is None:
        desc_col = df.columns[1]

    df[code_col] = df[code_col].astype(str)
    df[desc_col] = df[desc_col].astype(str)

    # Combined search text
    df["__search"] = (df[code_col] + " " + df[desc_col]).str.lower()

    # Category (first 3 chars)
    df["category"] = df[code_col].str[:3]

    # Chapter (first letter)
    df["chapter_letter"] = df[code_col].str[0].str.upper()
    df["chapter_name"] = df["chapter_letter"].apply(map_chapter)

    return df, code_col, desc_col


# ---------------------------
# PERPLEXITY AI CALL
# ---------------------------
def call_perplexity_icd_explain(icd_code: str, description: str) -> str:
    """
    Calls Perplexity AI to explain the disease in simple, safe language.
    Requires PERPLEXITY_API_KEY in st.secrets.
    """
    api_key = st.secrets.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        return (
            "AI is not configured yet. Please add PERPLEXITY_API_KEY to your "
            "Streamlit secrets to enable disease explanations."
        )

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are a medical information assistant. "
        "Explain conditions in clear, non-alarming, patient-friendly language. "
        "Include typical symptoms, general risk factors, and common treatment options. "
        "Always remind users that this is general information and not a diagnosis or medical advice, "
        "and that they should speak with a licensed clinician for personal decisions."
    )

    user_prompt = (
        f"ICD-10 code: {icd_code}\n"
        f"Condition description: {description}\n\n"
        "Explain what this condition generally means for a patient. "
        "Structure the answer with short sections: What it is, Common symptoms, "
        "When to seek medical care, and General treatment options."
    )

    payload = {
        "model": "sonar-small-online",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 500,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code != 200:
            return f"AI error (status {resp.status_code}). Please try again later."
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return "AI did not return any content. Please try again."
        return content
    except Exception as e:
        return f"AI request failed: {e}"


# ---------------------------
# RENDER ONE RESULT CARD + AI BUTTON
# ---------------------------
def render_icd_card(row, code_col, desc_col, related_df: pd.DataFrame):
    code = row[code_col]
    desc = row[desc_col]
    chapter_name = row.get("chapter_name", "Unknown")
    category = row.get("category", "")

    tags = []
    if chapter_name and chapter_name != "Unknown":
        tags.append(chapter_name)
    if category:
        tags.append(f"Category {category}")

    tag_text = " · ".join(tags)

    # Card layout
    st.markdown(
        f"""
        <div class="hanvion-card">
            <div class="hanvion-code">{code}</div>
            <div class="hanvion-desc">{desc}</div>
            <div class="hanvion-tags">{tag_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Buttons row
    bcol1, bcol2 = st.columns([1.7, 3])
    with bcol1:
        # Copy button (JS in HTML)
        st.markdown(
            f"""
            <button class="hanvion-copy-btn" onclick="navigator.clipboard.writeText('{code}')">
                Copy code
            </button>
            """,
            unsafe_allow_html=True,
        )

    with bcol2:
        key_learn = f"ai_learn_{code}"
        if st.button("Learn about this condition (AI)", key=key_learn):
            # Call AI and store result in session_state
            explanation = call_perplexity_icd_explain(code, desc)
            st.session_state[f"ai_explain_{code}"] = explanation

    # Show AI explanation if exists
    exp_key = f"ai_explain_{code}"
    if exp_key in st.session_state:
        with st.expander("AI explanation (for educational use only)", expanded=False):
            st.markdown(st.session_state[exp_key])

    # Related codes (same category, if available)
    if related_df is not None and len(related_df) > 1:
        with st.expander("View related codes in this category"):
            for _, r in related_df.iterrows():
                r_code = r[code_col]
                r_desc = r[desc_col]
                if r_code == code:
                    continue
                st.markdown(f"**{r_code}** — {r_desc}")


# ---------------------------
# MAIN APP
# ---------------------------
def main():
    # Header
    st.markdown(
        """
        <div class="hanvion-header noselect">
            <div class="hanvion-header-title">Hanvion Health · ICD-10 Explorer</div>
            <div class="hanvion-header-subtitle">
                Fast, clinical-grade ICD-10 lookup with filters, related codes, CSV export, and AI-based disease explanations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        df, code_col, desc_col = load_icd10()
    except Exception as e:
        st.error(
            "❌ Could not load the ICD-10 Excel file.\n\n"
            f"Expected file: `{ICD_XLSX}` in the same folder.\n\n"
            f"Error: {e}"
        )
        return

    # -------------- Search + Filters --------------
    search_col, _ = st.columns([2, 1])
    with search_col:
        query = st.text_input(
            "Search ICD-10 code or description",
            placeholder="e.g., E11, diabetes, hypertension, cough…",
        )

    col1, col2, col3 = st.columns([1.4, 1.4, 1])
    with col1:
        chapter_options = ["All Chapters"] + sorted(df["chapter_name"].dropna().unique().tolist())
        chapter_filter = st.selectbox("Filter by Chapter", options=chapter_options, index=0)
    with col2:
        category_filter = st.text_input("Filter by Category (e.g., E11)", placeholder="Optional")
    with col3:
        exact_match = st.checkbox("Starts with code")

    # Suggestions
    if query and len(query.strip()) >= 2:
        q = query.strip().lower()
        sugg = df[df[code_col].str.lower().str.startswith(q)][code_col].head(5)
        if not sugg.empty:
            st.caption("Suggestions:")
            st.write(", ".join(sugg.astype(str).tolist()))

    st.markdown("---")

    # Guard for short query
    if not query or len(query.strip()) < 2:
        st.info("Type at least 2 characters to start searching ICD-10 codes.")
        return

    q = query.strip().lower()

    # -------------- Build mask --------------
    if exact_match:
        mask = df[code_col].str.lower().str.startswith(q)
    else:
        mask = df["__search"].str.contains(q, na=False)

    if chapter_filter != "All Chapters":
        mask &= df["chapter_name"] == chapter_filter

    if category_filter.strip():
        cf = category_filter.strip().upper()
        mask &= df["category"].str.upper().str.startswith(cf)

    results = df[mask]
    total = len(results)

    st.markdown(f"**{total}** matching ICD-10 code(s) found.")

    if total == 0:
        st.warning("No results found. Try different keywords or remove some filters.")
        return

    # -------------- CSV Export --------------
    export_df = results.drop(columns=["__search"], errors="ignore")
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download results as CSV",
        data=csv_bytes,
        file_name="icd10_results_hanvion.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # -------------- Pagination --------------
    rows_per_page = 30
    pages = max(1, (total - 1) // rows_per_page + 1)

    col_page, col_info = st.columns([1, 3])
    with col_page:
        page = st.number_input("Page", min_value=1, max_value=pages, value=1, step=1)
    with col_info:
        start = (page - 1) * rows_per_page
        end = min(start + rows_per_page, total)
        st.caption(f"Showing {start+1}–{end} of {total} codes")

    page_df = results.iloc[start:end]

    # For related codes – group by category in the filtered results set
    grouped_by_category = dict(tuple(results.groupby("category")))

    # -------------- Render Cards --------------
    for _, row in page_df.iterrows():
        cat = row.get("category", None)
        related_df = grouped_by_category.get(cat, None)
        render_icd_card(row, code_col, desc_col, related_df)

    # Small disclaimer
    st.markdown(
        """
        <p style="font-size:11px; color:#6b7280; margin-top:20px;" class="noselect">
        AI explanations are for educational purposes only and are not a substitute for professional medical advice,
        diagnosis, or treatment. Always consult a licensed clinician for personal medical decisions.
        </p>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
