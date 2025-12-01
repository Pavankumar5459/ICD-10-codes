# =========================================================
# Hanvion Health – Advanced ICD-10 Explorer (Theme B)
# =========================================================

import streamlit as st
import pandas as pd

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
# RENDER ONE RESULT CARD
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

    st.markdown(
        f"""
        <div class="hanvion-card">
            <div class="hanvion-code">{code}</div>
            <div class="hanvion-desc">{desc}</div>
            <div class="hanvion-tags">{tag_text}</div>
            <button class="hanvion-copy-btn" onclick="navigator.clipboard.writeText('{code}')">
                Copy code
            </button>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
                Fast, clinical-grade ICD-10 lookup with filters, related codes, and export.
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


if __name__ == "__main__":
    main()
