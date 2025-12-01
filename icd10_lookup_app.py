import os
import streamlit as st
import pandas as pd

ICD_XLSX = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"
ICD_PARQUET = "section111validicd10.parquet"


# ---------------------------
# Chapter mapping (approx.)
# ---------------------------
def map_chapter(letter: str) -> str:
    if not isinstance(letter, str) or not letter:
        return "Unknown"

    l = letter.upper()

    # Very simplified high-level mapping by first letter
    if l in ["A", "B"]:
        return "A00-B99 · Infectious & Parasitic Diseases"
    if l in ["C", "D"]:
        return "C00-D49 · Neoplasms / Blood Disorders"
    if l == "E":
        return "E00-E89 · Endocrine, Nutritional, Metabolic"
    if l == "F":
        return "F01-F99 · Mental & Behavioural Disorders"
    if l == "G":
        return "G00-G99 · Nervous System"
    if l == "H":
        return "H00-H95 · Eye, Ear & Adnexa"
    if l == "I":
        return "I00-I99 · Circulatory System (Cardiology)"
    if l == "J":
        return "J00-J99 · Respiratory System"
    if l == "K":
        return "K00-K95 · Digestive System"
    if l == "L":
        return "L00-L99 · Skin/Subcutaneous Tissue"
    if l == "M":
        return "M00-M99 · Musculoskeletal"
    if l == "N":
        return "N00-N99 · Genitourinary"
    if l == "O":
        return "O00-O9A · Pregnancy, Childbirth"
    if l == "P":
        return "P00-P96 · Perinatal Conditions"
    if l == "Q":
        return "Q00-Q99 · Congenital Malformations"
    if l == "R":
        return "R00-R99 · Symptoms & Abnormal Findings"
    if l == "S" or l == "T":
        return "S00-T88 · Injury, Poisoning"
    if l == "V" or l == "W" or l == "X" or l == "Y":
        return "V00-Y99 · External Causes"
    if l == "Z":
        return "Z00-Z99 · Factors Influencing Health Status"

    return "Other / Unmapped"


# ---------------------------
# Load + preprocess (cached)
# ---------------------------
@st.cache_data(show_spinner="Loading ICD-10 dataset…")
def load_icd10():
    """
    Load ICD-10 data, with Parquet acceleration if available.
    Returns: df, code_col, desc_col
    """
    if os.path.exists(ICD_PARQUET):
        df = pd.read_parquet(ICD_PARQUET)
    else:
        df = pd.read_excel(ICD_XLSX, dtype=str)
        df.to_parquet(ICD_PARQUET, index=False)

    # Clean column names
    df.columns = [c.strip().replace("\n", " ").replace("  ", " ") for c in df.columns]

    # Detect code + description columns
    code_candidates = ["ICD10", "ICD-10 Code", "Code", "DIAG_CD"]
    desc_candidates = ["Description", "LONG_DESCRIPTION", "LONG_DESC", "Full Description"]

    code_col = None
    desc_col = None

    for c in df.columns:
        if c in code_candidates and code_col is None:
            code_col = c
        if c in desc_candidates and desc_col is None:
            desc_col = c

    if code_col is None:
        code_col = df.columns[0]
    if desc_col is None:
        desc_col = df.columns[1]

    # Make sure code/desc are string
    df[code_col] = df[code_col].astype(str)
    df[desc_col] = df[desc_col].astype(str)

    # Combined search text for fast substring search
    df["__search"] = (
        df[code_col].fillna("") + " " +
        df[desc_col].fillna("")
    ).str.lower()

    # Category = first 3 chars; Chapter letter = first char
    df["category"] = df[code_col].str[:3]
    df["chapter_letter"] = df[code_col].str[0].str.upper()
    df["chapter_name"] = df["chapter_letter"].apply(map_chapter)

    return df, code_col, desc_col


# ---------------------------
# Render one ICD card
# ---------------------------
def render_icd_card(row, code_col, desc_col, related_df: pd.DataFrame):
    code = row[code_col]
    desc = row[desc_col]
    category = row.get("category", "")
    chapter_name = row.get("chapter_name", "Unknown")

    # Build tags
    tags = []
    if category:
        tags.append(f"Category: {category}")
    if chapter_name and chapter_name != "Unknown":
        tags.append(chapter_name)

    tags_text = " · ".join(tags)

    st.markdown(
        f"""
        <div style="
            padding: 12px 14px;
            border-radius: 10px;
            border: 1px solid #d4dbe8;
            background: #f8fafc;
            margin-bottom: 10px;
        ">
            <div style="font-size: 18px; font-weight: 700; color:#0f172a;">
                {code}
            </div>
            <div style="font-size: 14px; color:#475569; margin-top:4px;">
                {desc}
            </div>
            <div style="font-size: 12px; color:#64748b; margin-top:6px;">
                {tags_text}
            </div>
            <div style="margin-top:8px;">
                <button onclick="navigator.clipboard.writeText('{code}')"
                    style="
                        padding:4px 10px;
                        border-radius:5px;
                        background:#2563eb;
                        color:white;
                        border:none;
                        cursor:pointer;
                        font-size:12px;
                    ">
                    Copy code
                </button>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Related codes (same category)
    if not related_df.empty:
        with st.expander("View related codes in this category"):
            for _, r in related_df.iterrows():
                r_code = r[code_col]
                r_desc = r[desc_col]
                if r_code == code:
                    continue
                st.markdown(f"**{r_code}** — {r_desc}")


# ---------------------------
# Main app
# ---------------------------
def main():
    st.set_page_config(page_title="ICD-10 Explorer", layout="wide")
    st.title("ICD-10 Explorer · CMS January 2026 Dataset")

    st.caption(
        "Fast search, filters, related codes, and CSV export — "
        "powered by the official CMS Section 111 ICD-10 list."
    )

    try:
        df, code_col, desc_col = load_icd10()
    except Exception as e:
        st.error(
            "Could not load the ICD-10 file.\n\n"
            f"Make sure `{ICD_XLSX}` is in the same folder as this app.\n\n"
            f"Error: {e}"
        )
        return

    # ---------------- Search + filters layout ----------------
    with st.container():
        col_search, col_opts = st.columns([2.5, 1.5])

        with col_search:
            query = st.text_input(
                "Search ICD-10 code or description",
                placeholder="Example: E11, diabetes, hypertension, cough…",
            )

        with col_opts:
            exact_code = st.checkbox("Exact code / starts-with match", value=False)

            # Chapter filter
            chapters = sorted(df["chapter_name"].dropna().unique().tolist())
            chapter_filter = st.selectbox(
                "Filter by Chapter",
                options=["All Chapters"] + chapters,
                index=0,
            )

            category_filter = st.text_input(
                "Filter by Category (e.g., E11, I10)",
                placeholder="Optional prefix",
            )

    st.markdown("---")

    # ---------------- Suggestions ----------------
    if query and len(query.strip()) >= 2:
        q_lower = query.strip().lower()
        sugg = df[df[code_col].str.lower().str.startswith(q_lower)][code_col].head(5)
        if not sugg.empty:
            st.caption("Suggestions (matching code prefix):")
            st.write(", ".join(sugg.astype(str).tolist()))

    # ---------------- Guard for empty query ----------------
    if not query or len(query.strip()) < 2:
        st.info("Type at least 2 characters to start searching ICD-10.")
        return

    q = query.strip().lower()

    # ---------------- Build mask ----------------
    mask = pd.Series(True, index=df.index)

    if exact_code:
        mask &= df[code_col].str.lower().str.startswith(q)
    else:
        mask &= df["__search"].str.contains(q, na=False)

    if chapter_filter != "All Chapters":
        mask &= (df["chapter_name"] == chapter_filter)

    if category_filter.strip():
        cat = category_filter.strip().upper()
        mask &= df["category"].str.upper().str.startswith(cat)

    results = df[mask]
    total = len(results)

    st.write(f"Found **{total}** matching ICD-10 code(s).")

    if total == 0:
        st.warning("No results found. Try another keyword, code, or remove some filters.")
        return

    # ---------------- CSV Export ----------------
    export_df = results.drop(columns=["__search"], errors="ignore")
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Download results as CSV",
        data=csv_bytes,
        file_name="icd10_results.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # ---------------- Pagination ----------------
    rows_per_page = 30
    pages = (total - 1) // rows_per_page + 1
    col_page, col_info = st.columns([1, 3])

    with col_page:
        if pages > 1:
            page = st.number_input(
                "Page",
                min_value=1,
                max_value=pages,
                value=1,
                step=1,
            )
        else:
            page = 1

    with col_info:
        start = (page - 1) * rows_per_page
        end = min(start + rows_per_page, total)
        st.caption(f"Showing {start+1}–{end} of {total} codes")

    page_df = results.iloc[start:end]

    # Build a small helper mapping category -> subset for related codes
    # (Only among the filtered result set to keep it light)
    by_cat = {
        cat: sub_df
        for cat, sub_df in page_df.groupby("category")
    }

    # ---------------- Render cards ----------------
    for _, row in page_df.iterrows():
        cat = row.get("category", None)
        related_df = pd.DataFrame()
        if cat in by_cat:
            related_df = by_cat[cat]
        render_icd_card(row, code_col, desc_col, related_df)


if __name__ == "__main__":
    main()
