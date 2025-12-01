# icd10_lookup_app.py
# Hanvion Health · ICD-10 Explorer with optional Perplexity AI helpers

import os
import textwrap
from typing import Optional, Tuple

import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    page_icon="💠",
    layout="wide",
)

# -----------------------------------------------------------------------------
# THEME (Hanvion style)
# -----------------------------------------------------------------------------
HANVION_CSS = """
<style>
/* Base layout */
.block-container {
    max-width: 1100px !important;
    padding-top: 1.5rem !important;
}

/* Typography */
body, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Code card */
.hanvion-card {
    background: #faf5ff;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    padding: 18px 20px;
    margin-bottom: 16px;
}

/* Code badge */
.hanvion-code-pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #4c1d95;
    color: #f9fafb;
    font-size: 11px;
    font-weight: 600;
}

/* Muted text */
.hanvion-muted {
    color: #6b7280;
    font-size: 12px;
}

/* Section label */
.hanvion-section-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 11px;
    color: #9ca3af;
}

/* Buttons */
.hanvion-button {
    border-radius: 999px !important;
}

/* Hide expand/collapse cursor highlight on headings */
h1, h2, h3, h4, h5 {
    user-select: none;
}

/* Expander title style */
.streamlit-expanderHeader {
    font-size: 13px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e5e7eb;
}
</style>
"""
st.markdown(HANVION_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------
DATA_FILE = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"


@st.cache_data(show_spinner=True)
def load_icd10_data() -> pd.DataFrame:
    """Load CMS ICD-10 Excel and normalize column names.

    Expected columns in file:
    - CODE
    - SHORT DESCRIPTION (VALID ICD-10 FY2025)
    - LONG DESCRIPTION (VALID ICD-10 FY2025)
    """
    df = pd.read_excel(DATA_FILE, dtype=str).fillna("")

    df = df.rename(
        columns={
            "CODE": "code",
            "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_description",
            "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_description",
        }
    )

    # Ensure required columns exist
    if "code" not in df.columns:
        raise ValueError("Dataset must contain a 'CODE' column.")

    if "short_description" not in df.columns:
        df["short_description"] = df["long_description"]

    if "long_description" not in df.columns:
        df["long_description"] = df["short_description"]

    # Simple derived columns
    if "chapter" not in df.columns:
        df["chapter"] = "N/A"
    if "category" not in df.columns:
        df["category"] = df["code"].str[:3]

    return df[["code", "short_description", "long_description", "chapter", "category"]]


# -----------------------------------------------------------------------------
# PERPLEXITY AI HELPER
# -----------------------------------------------------------------------------
def get_pplx_key() -> Optional[str]:
    key = os.getenv("PPLX_API_KEY")
    if key:
        return key
    try:
        key = st.secrets.get("PPLX_API_KEY", None)
    except Exception:
        key = None
    return key


def call_perplexity(
    user_prompt: str,
    system_prompt: str,
    temperature: float = 0.3,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Call Perplexity's /chat/completions endpoint.
    Returns (content, error_message).
    """
    api_key = get_pplx_key()
    if not api_key:
        return None, "AI is not configured. Add PPLX_API_KEY in your Streamlit secrets."

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
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, json=payload, timeout=25)
    except Exception as e:
        return None, f"AI network error: {e}"

    if resp.status_code != 200:
        return None, f"AI error (status {resp.status_code}). Please try again later."

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content, None
    except Exception as e:
        return None, f"AI response parsing error: {e}"


# -----------------------------------------------------------------------------
# SIMPLE UTILITIES
# -----------------------------------------------------------------------------
def wrap(text: str, width: int = 90) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def filter_icd10(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Case-insensitive filter on code + descriptions."""
    if not query:
        return df.iloc[0:0]  # empty
    q = query.strip().lower()
    mask = (
        df["code"].str.lower().str.contains(q, na=False)
        | df["short_description"].str.lower().str.contains(q, na=False)
        | df["long_description"].str.lower().str.contains(q, na=False)
    )
    return df[mask]


def symptom_suggest(df: pd.DataFrame, text: str, limit: int = 10) -> pd.DataFrame:
    """Very lightweight 'symptom to ICD code' helper using text match only."""
    if not text:
        return df.iloc[0:0]
    q = text.strip().lower()
    mask = (
        df["short_description"].str.lower().str.contains(q, na=False)
        | df["long_description"].str.lower().str.contains(q, na=False)
    )
    return df[mask].head(limit)


# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
def main() -> None:
    df = load_icd10_data()
    enable_ai = get_pplx_key() is not None

    st.markdown("### Hanvion Health · ICD-10 Explorer")
    st.markdown(
        "Search ICD-10 codes, view structured context, and optionally explore "
        "AI-generated educational summaries. This tool is **not** a billing "
        "or diagnostic system."
    )

    st.markdown('<div class="hanvion-section-label">Search</div>', unsafe_allow_html=True)

    col_q, col_n = st.columns([4, 1])
    with col_q:
        query = st.text_input(
            "Search by ICD-10 code or diagnosis",
            placeholder="Example: E11, asthma, fracture",
        )
    with col_n:
        page_size = st.number_input(
            "Results per page",
            min_value=10,
            max_value=100,
            value=20,
            step=10,
        )

    col_page, _ = st.columns([1, 3])
    with col_page:
        page_num = st.number_input("Page", min_value=1, value=1, step=1)

    st.divider()

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------
    if not query.strip():
        st.info("Start by entering an ICD-10 code or diagnosis in the search box above.")
        st.markdown("---")
    else:
        results = filter_icd10(df, query)
        total = len(results)

        if total == 0:
            st.warning("No matching ICD-10 codes found. Try a broader term or different wording.")
        else:
            st.markdown(
                f"Showing results **{min((page_num-1)*page_size+1, total)}–"
                f"{min(page_num*page_size, total)}** of **{total}**."
            )

            start = (page_num - 1) * page_size
            end = start + page_size
            page_df = results.iloc[start:end]

            for _, row in page_df.iterrows():
                with st.container():
                    st.markdown('<div class="hanvion-card">', unsafe_allow_html=True)

                    # Header
                    st.markdown(
                        f'<span class="hanvion-code-pill">{row["code"]}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"#### {row['short_description']}",
                        help="Educational use only.",
                    )

                    if row["long_description"]:
                        st.markdown(row["long_description"])
                    st.markdown(
                        f'<p class="hanvion-muted">Chapter: {row.get("chapter","N/A")} · '
                        f'Category: {row.get("category","N/A")}</p>',
                        unsafe_allow_html=True,
                    )

                    # --- Add-on: Clinical explanation (AI or fallback) -----------------
                    with st.expander("Clinical explanation (educational only)"):
                        st.markdown(
                            "These summaries are generated for learning purposes only "
                            "and are **not** medical advice."
                        )

                        if enable_ai:
                            if st.button(
                                "Generate clinical explanation",
                                key=f"explain_{row['code']}",
                            ):
                                with st.spinner("Asking AI for an explanation..."):
                                    sys_prompt = (
                                        "You are a clinical documentation assistant. "
                                        "Explain ICD-10 codes in clear, educational language "
                                        "for students and health data analysts. "
                                        "Do not give treatment recommendations, and explicitly "
                                        "state that this is not medical advice."
                                    )
                                    user_prompt = (
                                        f"Explain ICD-10 code {row['code']} "
                                        f"({row['short_description']}). "
                                        f"Use 3–5 bullet points."
                                    )
                                    content, err = call_perplexity(user_prompt, sys_prompt)
                                if err:
                                    st.error(err)
                                elif content:
                                    st.markdown(content)
                        else:
                            st.info(
                                "AI explanation is not configured. Add `PPLX_API_KEY` to enable "
                                "Perplexity-powered summaries."
                            )
                            st.markdown(
                                "- Code context: "
                                f"{wrap(row['long_description'] or row['short_description'])}"
                            )

                    # --- Add-on: Patient-friendly summary (still educational) ----------
                    with st.expander("Patient-friendly summary (educational only)"):
                        if enable_ai:
                            if st.button(
                                "Generate simple explanation",
                                key=f"patient_{row['code']}",
                            ):
                                with st.spinner("Generating a simple explanation..."):
                                    sys_prompt = (
                                        "You explain medical concepts in simple language. "
                                        "Audience: adults with no medical training. "
                                        "Keep it short (about 120 words), avoid scary language, "
                                        "and never give treatment advice."
                                    )
                                    user_prompt = (
                                        f"Explain ICD-10 code {row['code']} "
                                        f"({row['short_description']})."
                                    )
                                    content, err = call_perplexity(user_prompt, sys_prompt)
                                if err:
                                    st.error(err)
                                elif content:
                                    st.markdown(content)
                        else:
                            st.info(
                                "AI is not configured. When enabled, this section will generate "
                                "a patient-friendly summary."
                            )

                    # --- Add-on: Code comparison (Feature D) ---------------------------
                    with st.expander("Compare with another ICD-10 code"):
                        st.markdown(
                            "Use this to understand conceptual differences between two codes. "
                            "Educational use only."
                        )
                        other = st.text_input(
                            "Code to compare with",
                            key=f"compare_input_{row['code']}",
                            placeholder="Example: A001",
                        )
                        if enable_ai and other.strip():
                            if st.button(
                                "Compare codes",
                                key=f"compare_btn_{row['code']}",
                            ):
                                with st.spinner("Comparing codes with AI..."):
                                    sys_prompt = (
                                        "You compare ICD-10 codes for documentation and analytics. "
                                        "Describe how the two codes differ in clinical concept, "
                                        "typical use, and any important exclusions. "
                                        "Do not give treatment advice."
                                    )
                                    user_prompt = (
                                        f"Compare ICD-10 codes {row['code']} "
                                        f"({row['short_description']}) and "
                                        f"{other.strip()}. "
                                        "Use bullet points and keep it concise."
                                    )
                                    content, err = call_perplexity(user_prompt, sys_prompt)
                                if err:
                                    st.error(err)
                                elif content:
                                    st.markdown(content)
                        elif not enable_ai:
                            st.info(
                                "AI comparison requires `PPLX_API_KEY`. Configure it to use this feature."
                            )

                    st.markdown("</div>", unsafe_allow_html=True)  # end card

    # -------------------------------------------------------------------------
    # Symptom-based helper (Feature E)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### Symptom helper (search-based — not a diagnosis tool)")
    st.markdown(
        "Type symptoms or a lay description to see **related ICD-10 codes** from the dataset. "
        "This is a keyword search to support learning and analytics — it is **not** a "
        "diagnostic suggestion."
    )

    symptom_text = st.text_input(
        "Describe symptoms or condition (optional)",
        placeholder="Example: chest pain, shortness of breath",
    )

    if symptom_text.strip():
        suggestions = symptom_suggest(df, symptom_text, limit=10)
        if len(suggestions) == 0:
            st.info("No codes matched those terms. Try different wording.")
        else:
            st.markdown(
                f"Showing {len(suggestions)} codes that mention similar terms "
                "in their descriptions:"
            )
            for _, srow in suggestions.iterrows():
                st.markdown(
                    f"- **{srow['code']}** — {srow['short_description']}"
                )

    # Footer
    st.markdown("---")
    st.markdown(
        '<p class="hanvion-muted">Hanvion Health · ICD-10 Lookup • '
        "Educational use only • Not for billing or medical decision-making.</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
