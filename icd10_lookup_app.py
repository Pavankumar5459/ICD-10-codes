# icd10_lookup_app.py
# Hanvion Health · ICD-10 Explorer with Perplexity AI (educational only)

import os
import math
import requests
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
#  Perplexity AI helpers
# ---------------------------------------------------------
def get_pplx_key() -> str | None:
    """Get Perplexity API key from environment or Streamlit secrets."""
    try:
        return os.getenv("PPLX_API_KEY") or st.secrets.get("PPLX_API_KEY")
    except Exception:
        return os.getenv("PPLX_API_KEY")


def ask_perplexity(prompt: str) -> dict:
    """
    Call Perplexity AI safely.
    Returns dict: {success: bool, response: str | None, error: str | None}
    """
    api_key = get_pplx_key()
    if not api_key:
        return {
            "success": False,
            "response": None,
            "error": "Perplexity API key not found. Add PPLX_API_KEY in your Streamlit secrets.",
        }

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-small-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a clinical explainer for ICD-10 codes. "
                    "You provide concise, structured, educational summaries only. "
                    "You never give medical advice or treatment recommendations."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)

        if res.status_code == 401:
            return {
                "success": False,
                "response": None,
                "error": "Perplexity API key is invalid or not authorized (401).",
            }

        if res.status_code >= 400:
            return {
                "success": False,
                "response": None,
                "error": f"Perplexity error {res.status_code}: {res.text}",
            }

        data = res.json()
        reply = data["choices"][0]["message"]["content"]
        return {"success": True, "response": reply, "error": None}

    except Exception as e:
        return {
            "success": False,
            "response": None,
            "error": f"Perplexity request failed: {e}",
        }


# ---------------------------------------------------------
#  Styling
# ---------------------------------------------------------
def inject_hanvion_css():
    st.markdown(
        """
        <style>
        body, input, textarea, button, select {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        .block-container {
            max-width: 1150px;
            padding-top: 1.5rem;
        }

        /* Headings */
        h1, h2, h3 {
            font-weight: 700;
            color: #111827;
        }

        /* ICD card */
        .icd-card {
            background: #fbf5ff;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
            padding: 18px 20px 16px 20px;
            margin-bottom: 14px;
        }

        .icd-code-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #7e22ce;
            color: white;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .icd-title {
            font-size: 18px;
            font-weight: 600;
            margin: 0 0 4px 0;
        }

        .icd-desc {
            font-size: 13px;
            color: #374151;
            margin: 0 0 4px 0;
        }

        .icd-meta {
            font-size: 11px;
            color: #6b7280;
            margin-top: 4px;
        }

        .muted-note {
            font-size: 11px;
            color: #6b7280;
        }

        [data-testid="stSidebar"] {
            background: #f9fafb;
            border-right: 1px solid #e5e7eb;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
#  Data loading
# ---------------------------------------------------------
@st.cache_data(show_spinner="Loading ICD-10 codes...")
def load_icd10_data() -> pd.DataFrame:
    """
    Load ICD-10 data from the CMS Excel file and standardise columns.
    We do NOT change the original file; we just map what exists.
    """
    # 1) Try CMS Excel
    if os.path.exists("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"):
        df_raw = pd.read_excel(
            "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
            dtype=str,
        )
    # 2) Fallback to CSV, if you ever have it
    elif os.path.exists("icd10_data.csv"):
        df_raw = pd.read_csv("icd10_data.csv", dtype=str)
    else:
        raise FileNotFoundError(
            "No ICD-10 data file found. Expected "
            "'section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx' "
            "or 'icd10_data.csv' in the app folder."
        )

    df_raw = df_raw.fillna("")
    cols = [str(c) for c in df_raw.columns]
    lower_cols = [c.lower().strip() for c in cols]

    # Helper to find a column by keywords
    def find_col(*keywords, default_index=None):
        for i, name in enumerate(lower_cols):
            if all(k in name for k in keywords):
                return cols[i]
        if default_index is not None and default_index < len(cols):
            return cols[default_index]
        return None

    code_col = find_col("icd", "code") or find_col("code") or cols[0]
    short_col = (
        find_col("short", "desc")
        or find_col("description")
        or find_col("desc")
        or cols[1]
        if len(cols) > 1
        else code_col
    )
    long_col = find_col("long", "desc") or short_col
    chapter_col = find_col("chapter")
    category_col = find_col("category")

    df = pd.DataFrame()
    df["code"] = df_raw[code_col].astype(str).str.strip()
    df["title"] = df_raw[short_col].astype(str).str.strip()
    df["description"] = df_raw[long_col].astype(str).str.strip()

    if chapter_col:
        df["chapter"] = df_raw[chapter_col].astype(str).str.strip()
    else:
        df["chapter"] = ""

    if category_col:
        df["category"] = df_raw[category_col].astype(str).str.strip()
    else:
        df["category"] = ""

    # Drop empty codes
    df = df[df["code"] != ""].reset_index(drop=True)
    return df


# ---------------------------------------------------------
#  Main UI
# ---------------------------------------------------------
def main():
    inject_hanvion_css()
    st.set_page_config(page_title="Hanvion Health · ICD-10 Explorer", page_icon="🧬", layout="wide")

    df = load_icd10_data()

    # ---- Header ----
    st.title("Hanvion Health · ICD-10 Explorer")
    st.markdown(
        "Search ICD-10 codes and view structured, educational context. "
        "This tool is **not** for billing or medical decision making."
    )

    st.markdown("---")

    # ---- Search Controls ----
    col_q, col_page_size = st.columns([3, 1])
    with col_q:
        query = st.text_input(
            "Search by ICD code or diagnosis",
            value="",
            placeholder="Example: E11, diabetes, asthma, fracture",
        ).strip()
    with col_page_size:
        page_size = st.number_input("Results per page", min_value=5, max_value=50, value=20, step=5)

    # Page selector (only relevant when we have results)
    page_number = st.number_input("Page", min_value=1, value=1, step=1)

    st.markdown("---")

    # ---- No query yet → do not show any codes ----
    if not query:
        st.info("Start by typing an ICD code or condition name above to see results.")
        st.markdown(
            f"<p class='muted-note'>Total ICD-10 codes available: {len(df):,}. Dataset for education only.</p>",
            unsafe_allow_html=True,
        )
        return

    # ---- Filter results ----
    mask_code = df["code"].str.contains(query, case=False, na=False)
    mask_title = df["title"].str.contains(query, case=False, na=False)
    mask_desc = df["description"].str.contains(query, case=False, na=False)
    df_filtered = df[mask_code | mask_title | mask_desc].reset_index(drop=True)

    total_results = len(df_filtered)
    if total_results == 0:
        st.warning("No ICD-10 codes matched your search. Try a different keyword or partial code.")
        return

    total_pages = max(1, math.ceil(total_results / page_size))
    # Clamp page_number
    if page_number > total_pages:
        page_number = total_pages

    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    page_df = df_filtered.iloc[start_idx:end_idx]

    st.caption(f"Showing {start_idx + 1:,}–{min(end_idx, total_results):,} of {total_results:,} matching codes.")

    # -------------------------------------------------
    # Render each ICD-10 card
    # -------------------------------------------------
    for row_idx, row in page_df.iterrows():
        code = row["code"]
        title = row["title"] or "(no title available)"
        desc = row["description"] or "No additional description in dataset."
        chapter = row["chapter"] or "N/A"
        category = row["category"] or "N/A"

        # Card layout
        card_html = f"""
        <div class="icd-card">
            <div class="icd-code-pill">{code}</div>
            <div class="icd-title">{title}</div>
            <p class="icd-desc">{desc}</p>
            <p class="icd-meta">Chapter: {chapter} · Category: {category}</p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # ---------- AI + comparison section ----------
        with st.expander("Clinical explanation (educational only)", expanded=False):
            st.markdown(
                "<p class='muted-note'>These explanations are for learning only and are not medical advice.</p>",
                unsafe_allow_html=True,
            )
            if st.button("Generate clinical explanation", key=f"clin_{start_idx + row_idx}"):
                with st.spinner("Generating explanation..."):
                    prompt = (
                        f"Provide a short clinical overview of ICD-10 code {code}: {title}. "
                        f"Use bullet points where useful. Include typical clinical context, "
                        f"but do NOT give treatment recommendations. "
                        f"Base it only on general medical knowledge."
                    )
                    result = ask_perplexity(prompt)

                if result["success"]:
                    st.write(result["response"])
                else:
                    st.error(result["error"])
                    # Simple fallback text
                    st.markdown(
                        f"""
                        **Basic summary (non-AI fallback)**  
                        • Code: **{code}**  
                        • Name: **{title}**  
                        • Description: {desc}
                        """,
                    )

        with st.expander("Patient-friendly summary (educational only)", expanded=False):
            st.markdown(
                "<p class='muted-note'>Use this to practise explaining conditions in simple language. "
                "It is not personalised medical advice.</p>",
                unsafe_allow_html=True,
            )
            if st.button("Generate simple explanation", key=f"simple_{start_idx + row_idx}"):
                with st.spinner("Generating simplified explanation..."):
                    prompt = (
                        f"Explain ICD-10 condition {code}: {title} in plain language for a non-medical reader. "
                        f"Keep it short (about 8–10 sentences). Do NOT give treatment instructions "
                        f"or say what medicine to take. Be neutral and educational."
                    )
                    result = ask_perplexity(prompt)

                if result["success"]:
                    st.write(result["response"])
                else:
                    st.error(result["error"])
                    st.markdown(
                        f"""
                        **Basic summary (non-AI fallback)**  
                        This code describes: **{title}**.  
                        The dataset does not contain more patient-friendly details for this code.
                        """
                    )

        with st.expander("Compare with another ICD-10 code", expanded=False):
            st.markdown(
                "<p class='muted-note'>Use this to contrast two codes conceptually. "
                "For billing or clinical use, always check official coding manuals.</p>",
                unsafe_allow_html=True,
            )
            other_code = st.text_input(
                "Other ICD-10 code to compare with",
                "",
                key=f"compare_input_{start_idx + row_idx}",
            ).strip()

            if st.button("Compare codes", key=f"compare_btn_{start_idx + row_idx}"):
                if not other_code:
                    st.warning("Please type another ICD-10 code to compare.")
                else:
                    # Try to pull basic info for other code from dataset
                    other_row = df[df["code"].str.upper() == other_code.upper()]
                    if not other_row.empty:
                        o = other_row.iloc[0]
                        oc_title = o["title"] or "(no title available)"
                        oc_desc = o["description"] or ""
                        st.markdown(
                            f"**Found {other_code.upper()} in dataset** — {oc_title}",
                        )
                        if oc_desc:
                            st.caption(oc_desc)

                    with st.spinner("Generating conceptual comparison..."):
                        prompt = (
                            f"Compare ICD-10 codes {code} ({title}) and {other_code}. "
                            "Explain how they are similar and how they differ in terms of condition type, "
                            "body system, and typical use, in a short bullet list. "
                            "Do not discuss billing amounts or treatment choices."
                        )
                        result = ask_perplexity(prompt)

                    if result["success"]:
                        st.write(result["response"])
                    else:
                        st.error(result["error"])
                        st.info(
                            "AI comparison is not available right now. "
                            "Make sure your Perplexity API key is configured."
                        )

        st.markdown("")  # small space between records

    # Footer note
    st.markdown("---")
    st.markdown(
        "<p class='muted-note'>Hanvion Health · ICD-10 Explorer is for educational purposes only and "
        "is not intended for diagnosis, treatment, billing, or coding decisions.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
#  Entrypoint
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
