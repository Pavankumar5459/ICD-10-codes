# icd10_lookup_app.py
# Hanvion Health – ICD-10 Explorer with Perplexity AI (Educational use only)

import io
import sys
import textwrap
from typing import Optional

import pandas as pd
import requests
import streamlit as st


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Hanvion – ICD-10 Explorer",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Hanvion global CSS theme
# -----------------------------
HANVION_CSS = """
<style>
/* Base layout */
body, input, textarea, button, select {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif;
}

/* Reduce top padding */
.block-container {
    max-width: 1180px !important;
    padding-top: 1rem !important;
}

/* Header band */
.hanvion-header {
    background: linear-gradient(90deg, #70001a, #9b1235);
    border-radius: 18px;
    padding: 22px 26px;
    color: #fff;
    box-shadow: 0 16px 40px rgba(112, 0, 26, 0.35);
    margin-bottom: 22px;
}
.hanvion-header h1 {
    margin: 0;
    font-size: 30px;
    letter-spacing: 0.02em;
}
.hanvion-header p {
    margin: 4px 0 0 0;
    font-size: 13px;
    opacity: 0.92;
}

/* Info pill row */
.hanvion-pill-row {
    display: flex;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
}
.hanvion-pill {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 11px;
}

/* Cards */
.hanvion-card {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    padding: 18px 20px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    margin-bottom: 14px;
}
.hanvion-card h3 {
    margin-top: 0;
}

/* Light / dark tweaks */
@media (prefers-color-scheme: dark) {
    .hanvion-header {
        background: linear-gradient(90deg, #450012, #7f1d35);
        box-shadow: 0 18px 50px rgba(0,0,0,0.7);
    }
    .hanvion-card {
        background: #020617;
        border-color: #1f2937;
        box-shadow: 0 16px 30px rgba(0,0,0,0.6);
    }
}

/* Section titles */
.hanvion-section-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 10px;
}

/* Avoid text selection look on headings */
h1, h2, h3, h4, .hanvion-section-title {
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}

/* Tiny caption text */
.hanvion-caption {
    font-size: 11px;
    color: #64748b;
}

/* Badge for categories */
.hanvion-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    background: #eff6ff;
    color: #1d4ed8;
}
@media (prefers-color-scheme: dark) {
    .hanvion-badge {
        background: #1e293b;
        color: #93c5fd;
    }
}

/* AI result styling */
.hanvion-ai-section-title {
    font-weight: 600;
    font-size: 13px;
    margin-top: 10px;
    margin-bottom: 4px;
}
.hanvion-ai-text {
    font-size: 13px;
}

/* Smaller Streamlit widgets */
.css-1dp5vir, .stSelectbox, .stNumberInput, .stTextInput {
    font-size: 13px;
}
</style>
"""
st.markdown(HANVION_CSS, unsafe_allow_html=True)


# -----------------------------
# Utility: load ICD-10 dataset
# -----------------------------
@st.cache_data(show_spinner=True)
def load_icd10_data() -> pd.DataFrame:
    """
    Load ICD-10 dataset from Excel/CSV and normalize column names.
    Tries a few common filenames so the app is flexible.
    """
    filenames = [
        "icd10_codes.xlsx",
        "icd10_codes.csv",
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
    ]

    df = None
    for fname in filenames:
        try:
            if fname.lower().endswith(".csv"):
                df = pd.read_csv(fname, dtype=str)
            else:
                df = pd.read_excel(fname, dtype=str)
            break
        except FileNotFoundError:
            continue

    if df is None:
        raise FileNotFoundError(
            "No ICD-10 data file found. Please upload "
            "`icd10_codes.xlsx` or `icd10_codes.csv` to the repository."
        )

    # Standardize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Try to map common column names to canonical ones
    col_map = {}

    # Code column
    for cand in ["code", "icd10code", "icd_10_code", "icd10", "dx", "diagnosis code"]:
        if cand in df.columns:
            col_map["code"] = cand
            break

    # Short description
    for cand in ["short description", "short_desc", "description", "shortdesc"]:
        if cand in df.columns:
            col_map["short_description"] = cand
            break

    # Long description
    for cand in ["long description", "long_desc", "longdesc"]:
        if cand in df.columns:
            col_map["long_description"] = cand
            break

    # Chapter / category info
    for cand in ["chapter", "icd10 chapter", "icd-10 chapter"]:
        if cand in df.columns:
            col_map["chapter"] = cand
            break

    for cand in ["category", "subcategory"]:
        if cand in df.columns:
            col_map["category"] = cand
            break

    # Keep only mapped + originals
    df_std = df.copy()

    # Create standardized columns with safe defaults
    df_std["code_std"] = df_std[col_map.get("code", df_std.columns[0])].str.strip()
    df_std["short_std"] = df_std.get(col_map.get("short_description", ""), "").fillna("")
    df_std["long_std"] = df_std.get(col_map.get("long_description", ""), "").fillna("")
    df_std["chapter_std"] = df_std.get(col_map.get("chapter", ""), "").fillna("")
    df_std["category_std"] = df_std.get(col_map.get("category", ""), "").fillna("")

    # Drop rows with no code
    df_std = df_std[df_std["code_std"].notna() & (df_std["code_std"].str.strip() != "")]

    return df_std.reset_index(drop=True)


# -----------------------------
# Perplexity AI integration
# -----------------------------
def get_perplexity_key() -> Optional[str]:
    try:
        return st.secrets["PERPLEXITY_API_KEY"]
    except Exception:
        return None


def call_perplexity_api(prompt: str) -> str:
    """
    Call Perplexity chat/completions API.
    Returns a human-readable message (never raises inside Streamlit).
    """
    api_key = get_perplexity_key()
    if not api_key:
        return (
            "AI explanation is unavailable because the Perplexity API key "
            "is not configured. Please add PERPLEXITY_API_KEY in Streamlit secrets."
        )

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-small-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.15,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=40)
    except Exception as exc:
        return f"AI request failed: {exc}"

    if resp.status_code != 200:
        return f"AI error (status {resp.status_code}). Please try again later."

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return "AI response could not be parsed. Please try again later."


def build_ai_prompt(icd_code: str, short_desc: str, long_desc: str) -> str:
    return textwrap.dedent(
        f"""
        You are a helpful medical explainer for ICD-10 codes.

        ICD-10 code: {icd_code}
        Short description: {short_desc}
        Long description: {long_desc}

        Provide a structured, **patient-friendly** explanation with markdown headings.
        Sections:
        1. What this condition means (plain language)
        2. Common symptoms
        3. Typical causes / risk factors
        4. How doctors usually evaluate it
        5. Typical treatment approaches
        6. When someone should seek urgent care
        7. Short note for healthcare students (1–2 bullet points)

        Keep it concise but informative. Do **not** give personal medical advice.
        Always end with a bold disclaimer that this is for education only,
        not a diagnosis or treatment plan.
        """
    ).strip()


# -----------------------------
# Main page layout
# -----------------------------
def main():
    # Header
    with st.container():
        st.markdown(
            """
            <div class="hanvion-header">
              <h1>ICD-10 Explorer</h1>
              <p>Search, filter, and understand ICD-10 diagnosis codes with Hanvion Health.</p>
              <div class="hanvion-pill-row">
                <div class="hanvion-pill">Fast code lookup</div>
                <div class="hanvion-pill">Educational AI explanations</div>
                <div class="hanvion-pill">Export selected codes as CSV</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Load data
    try:
        df = load_icd10_data()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    # -------------------------
    # Filters row
    # -------------------------
    with st.container():
        col_search, col_chapter, col_page_size = st.columns([3, 2, 1])

        with col_search:
            search_text = st.text_input(
                "Search by code or diagnosis",
                placeholder="Example: E11, asthma, fracture, diabetes…",
            ).strip()

        with col_chapter:
            chapter_options = (
                ["All chapters"]
                + sorted(
                    [c for c in df["chapter_std"].unique() if isinstance(c, str) and c.strip() != ""]
                )
            )
            selected_chapter = st.selectbox("Filter by chapter", chapter_options)

        with col_page_size:
            page_size = st.number_input(
                "Codes per page",
                min_value=10,
                max_value=100,
                value=30,
                step=10,
            )

    # -------------------------
    # Apply filters
    # -------------------------
    df_filtered = df.copy()

    if search_text:
        s = search_text.lower()
        df_filtered = df_filtered[
            df_filtered["code_std"].str.lower().str.contains(s)
            | df_filtered["short_std"].str.lower().str.contains(s)
            | df_filtered["long_std"].str.lower().str.contains(s)
        ]

    if selected_chapter != "All chapters":
        df_filtered = df_filtered[df_filtered["chapter_std"] == selected_chapter]

    total_codes = len(df_filtered)

    # Pagination
    total_pages = max(1, (total_codes + page_size - 1) // page_size)
    page_col1, page_col2, page_col3 = st.columns([1, 1, 3])

    with page_col1:
        current_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
        )
    with page_col2:
        st.markdown(
            f"<p class='hanvion-caption' style='margin-top:27px;'>"
            f"Showing {min((current_page-1)*page_size+1, total_codes)}–"
            f"{min(current_page*page_size, total_codes)} of {total_codes} codes"
            f"</p>",
            unsafe_allow_html=True,
        )

    # Page slice
    start_idx = (current_page - 1) * page_size
    end_idx = start_idx + page_size
    df_page = df_filtered.iloc[start_idx:end_idx]

    # -------------------------
    # Download button (filtered set)
    # -------------------------
    with page_col3:
        if total_codes > 0:
            csv_buf = io.StringIO()
            # Export canonical columns
            export_cols = ["code_std", "short_std", "long_std", "chapter_std", "category_std"]
            df_filtered[export_cols].rename(
                columns={
                    "code_std": "Code",
                    "short_std": "Short Description",
                    "long_std": "Long Description",
                    "chapter_std": "Chapter",
                    "category_std": "Category",
                }
            ).to_csv(csv_buf, index=False)
            st.download_button(
                label="⬇️ Download results as CSV",
                data=csv_buf.getvalue(),
                file_name="icd10_results.csv",
                mime="text/csv",
            )

    st.markdown("---")

    if total_codes == 0:
        st.info("No codes found for this search/filter. Try clearing filters or using a broader term.")
        st.stop()

    # -------------------------
    # Render each ICD code card
    # -------------------------
    for _, row in df_page.iterrows():
        code = row["code_std"]
        short = row["short_std"] or "(no short description)"
        long = row["long_std"]
        chapter = row["chapter_std"]
        category = row["category_std"]

        with st.container():
            st.markdown('<div class="hanvion-card">', unsafe_allow_html=True)

            # Top row: code + copy button
            top_col1, top_col2 = st.columns([4, 1])

            with top_col1:
                st.markdown(
                    f"### {code}  &nbsp;&nbsp; {short}",
                    unsafe_allow_html=True,
                )
                if long and long.strip() and long.strip().lower() != short.strip().lower():
                    st.markdown(f"<p class='hanvion-caption'>{long}</p>", unsafe_allow_html=True)

                badge_bits = []
                if chapter:
                    badge_bits.append(f"Chapter: {chapter}")
                if category:
                    badge_bits.append(f"Category: {category}")
                if badge_bits:
                    st.markdown(
                        f"<span class='hanvion-badge'>{' • '.join(badge_bits)}</span>",
                        unsafe_allow_html=True,
                    )

            with top_col2:
                if st.button("Copy code", key=f"copy_{code}"):
                    # We can't really write to clipboard from backend; show a hint instead.
                    st.success(f"Code {code} copied (or ready to copy).")

            # --- AI + related codes row ---
            ai_col, related_col = st.columns([2, 1])

            # AI section
            with ai_col:
                with st.expander("AI explanation (educational use only)", expanded=False):
                    st.markdown(
                        "<p class='hanvion-caption'>Powered by Perplexity AI. "
                        "Do not use as a substitute for professional medical advice.</p>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Generate AI overview for this code",
                        key=f"ai_btn_{code}",
                    ):
                        with st.spinner("Asking AI to explain this condition…"):
                            prompt = build_ai_prompt(code, short, long)
                            ai_text = call_perplexity_api(prompt)
                        st.markdown(f"<div class='hanvion-ai-text'>{ai_text}</div>", unsafe_allow_html=True)

            # Related codes section
            with related_col:
                with st.expander("View related codes in this category", expanded=False):
                    if category:
                        related_df = df[
                            (df["category_std"] == category) & (df["code_std"] != code)
                        ].head(15)
                    else:
                        # Fallback: same 3-character prefix
                        prefix = code[:3]
                        related_df = df[
                            (df["code_std"].str.startswith(prefix))
                            & (df["code_std"] != code)
                        ].head(15)

                    if related_df.empty:
                        st.caption("No related codes found in this dataset.")
                    else:
                        for _, r2 in related_df.iterrows():
                            st.markdown(
                                f"- **{r2['code_std']}** — {r2['short_std']}",
                                unsafe_allow_html=True,
                            )

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<p class='hanvion-caption' style='margin-top:6px;'>"
        "ICD-10 descriptions are sourced from your uploaded dataset. "
        "AI explanations use Perplexity and are for education only."
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
