import os
import textwrap
from typing import Optional, List

import pandas as pd
import requests
import streamlit as st


# =========================================================
# 1. PAGE CONFIG & GLOBAL THEME
# =========================================================

st.set_page_config(
    page_title="Hanvion Health – ICD-10 Explorer",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_hanvion_css() -> None:
    """Global light + dark Hanvion theme."""
    st.markdown(
        """
        <style>
        /* Base font */
        body, input, textarea, button, select {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, Helvetica, Arial, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        .block-container {
            max-width: 1200px !important;
            padding-top: 1.5rem !important;
        }

        /* HEADINGS – prevent text-selection look */
        h1, h2, h3, h4, h5 {
            user-select: none;
        }

        /* LIGHT MODE */
        @media (prefers-color-scheme: light) {
            .hanvion-banner {
                background: linear-gradient(90deg, #0f172a, #1d3557);
                color: #f9fafb;
                border-radius: 18px;
                padding: 22px 26px;
                box-shadow: 0 20px 40px rgba(15, 23, 42, 0.35);
                border: 1px solid rgba(148, 163, 184, 0.4);
            }

            .hanvion-card {
                background: #ffffff;
                border-radius: 14px;
                padding: 18px 20px;
                border: 1px solid #e2e8f0;
                box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
            }

            .hanvion-chip {
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 11px;
                background: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #bfdbfe;
            }

            .hanvion-muted {
                color: #64748b;
            }

            [data-testid="stSidebar"] {
                background: #f8fafc;
                border-right: 1px solid #e2e8f0;
            }

            .code-pill {
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                background: #0f172a;
                color: #e5e7eb;
                font-size: 13px;
                font-weight: 600;
            }
        }

        /* DARK MODE */
        @media (prefers-color-scheme: dark) {
            .hanvion-banner {
                background: linear-gradient(90deg, #020617, #111827);
                color: #e5e7eb;
                border-radius: 18px;
                padding: 22px 26px;
                box-shadow: 0 24px 45px rgba(0, 0, 0, 0.7);
                border: 1px solid #1f2937;
            }

            .hanvion-card {
                background: #020617;
                border-radius: 14px;
                padding: 18px 20px;
                border: 1px solid #1e293b;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.8);
            }

            .hanvion-chip {
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 11px;
                background: #111827;
                color: #e5e7eb;
                border: 1px solid #374151;
            }

            .hanvion-muted {
                color: #9ca3af;
            }

            [data-testid="stSidebar"] {
                background: #020617;
                border-right: 1px solid #111827;
                color: #e5e7eb;
            }

            .code-pill {
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                background: #f9fafb;
                color: #020617;
                font-size: 13px;
                font-weight: 600;
            }

            label, .stSelectbox label, .stTextInput label {
                color: #e5e7eb !important;
            }
        }

        /* Sidebar typography */
        .sidebar-title {
            font-size: 22px;
            font-weight: 800;
            margin-bottom: 2px;
        }
        .sidebar-subtitle {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 12px;
        }
        .sidebar-section {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #9ca3af;
            margin-top: 12px;
            margin-bottom: 6px;
        }

        .small-label {
            font-size: 12px;
            font-weight: 500;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_hanvion_css()


# =========================================================
# 2. DATA LOADING HELPERS
# =========================================================

def _find_existing_path() -> Optional[str]:
    """Try a few common locations for the ICD-10 Excel file."""
    candidates = [
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        "data/section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        "icd10_codes.xlsx",
        "data/icd10_codes.xlsx",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Return the first column name containing any of the keywords."""
    lowered = {c.lower(): c for c in df.columns}
    for key in keywords:
        key = key.lower()
        for low_name, original in lowered.items():
            if key in low_name:
                return original
    return None


@st.cache_data(show_spinner="Loading ICD-10 codes …")
def load_icd10_data() -> pd.DataFrame:
    """
    Load the ICD-10 dataset and normalize into:
    code, short_description, long_description, chapter, category
    """
    path = _find_existing_path()
    if not path:
        st.error(
            "ICD-10 dataset not found. Please upload "
            "`section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx` "
            "to the app folder."
        )
        st.stop()

    if path.lower().endswith(".xlsx"):
        df_raw = pd.read_excel(path)
    else:
        df_raw = pd.read_csv(path)

    # Robust column detection
    code_col = _find_column(df_raw, ["code"])
    short_col = _find_column(df_raw, ["short description", "short desc"])
    long_col = _find_column(df_raw, ["long description", "long desc"])
    chapter_col = _find_column(df_raw, ["chapter"])
    status_col = _find_column(df_raw, ["status", "included", "excluded"])

    df = pd.DataFrame()
    df["code"] = df_raw[code_col].astype(str).str.strip() if code_col else ""
    df["short_description"] = (
        df_raw[short_col].astype(str).str.strip() if short_col else ""
    )
    df["long_description"] = (
        df_raw[long_col].astype(str).str.strip() if long_col else ""
    )
    df["chapter"] = df_raw[chapter_col].astype(str).str.strip() if chapter_col else ""
    df["status"] = df_raw[status_col].astype(str).str.strip() if status_col else ""

    # Category / group helper
    df["category"] = df["code"].str.extract(r"^([A-Z]\\d{2})", expand=False)
    df["search_blob"] = (
        df["code"]
        + " "
        + df["short_description"]
        + " "
        + df["long_description"]
        + " "
        + df["chapter"]
    ).str.lower()

    df = df.dropna(subset=["code"]).reset_index(drop=True)
    return df


# =========================================================
# 3. PERPLEXITY API HELPER
# =========================================================

def get_pplx_api_key() -> Optional[str]:
    """Read Perplexity API key from env or Streamlit secrets."""
    key = os.getenv("PPLX_API_KEY")
    if not key:
        try:
            key = st.secrets.get("PPLX_API_KEY", None)  # type: ignore[attr-defined]
        except Exception:
            key = None
    return key


def call_perplexity_icd_explanation(
    code: str,
    short_desc: str,
    long_desc: str,
    chapter: str,
) -> str:
    """
    Call Perplexity's chat completions API to get a brief
    patient-friendly explanation. Returns either text or an error message.
    """
    api_key = get_pplx_api_key()
    if not api_key:
        return (
            "AI explanation is not configured. "
            "Please add `PPLX_API_KEY` to Streamlit secrets or environment."
        )

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are a clinical educator. Explain ICD-10 codes to patients in clear, "
        "simple language (US English). Keep it factual, short (3–5 bullet points), "
        "and remind that this is not a diagnosis or personal medical advice."
    )

    user_prompt = textwrap.dedent(
        f"""
        Code: {code}
        Short description: {short_desc}
        Long description: {long_desc}
        ICD-10 chapter: {chapter}

        Explain what this diagnosis usually means, typical symptoms or scenarios, and
        when a person should talk to a clinician. Do NOT mention ICD-10 or billing.
        """
    ).strip()

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return f"AI error (status {resp.status_code}). Please try again later."

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            return "AI did not return any text. Please try again later."
        return content

    except Exception as e:  # network / parsing errors
        return f"AI error: {e}"


# =========================================================
# 4. UI HELPERS
# =========================================================

def render_sidebar(df: pd.DataFrame) -> dict:
    """Sidebar filters & info. Returns a dict of filter values."""
    st.sidebar.markdown(
        '<div class="sidebar-title">Hanvion Health</div>'
        '<div class="sidebar-subtitle">ICD-10 Lookup • Education</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="sidebar-section">Search Filters</div>',
        unsafe_allow_html=True,
    )

    query = st.sidebar.text_input(
        "Search by code or diagnosis",
        placeholder="Example: diabetes, asthma, E11.9",
    )

    code_prefix = st.sidebar.selectbox(
        "Code starts with",
        ["All"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)],
        index=0,
    )

    include_status = "All"
    if "status" in df.columns and df["status"].notna().any():
        options = ["All"] + sorted(df["status"].dropna().unique().tolist())
        include_status = st.sidebar.selectbox("Status filter", options)

    page_size = st.sidebar.slider("Codes per page", 10, 50, 30, step=5)

    st.sidebar.markdown(
        '<div class="sidebar-section">Dataset</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        f"{len(df):,} ICD-10 codes loaded. Not a billing tool. "
        "Educational lookup only."
    )

    return {
        "query": query,
        "code_prefix": code_prefix,
        "status": include_status,
        "page_size": page_size,
    }


def apply_filters(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    df_f = df.copy()

    # Code prefix filter
    prefix = params.get("code_prefix", "All")
    if prefix != "All":
        df_f = df_f[df_f["code"].str.startswith(prefix)]

    # Status filter (if present)
    status = params.get("status", "All")
    if status != "All" and "status" in df_f.columns:
        df_f = df_f[df_f["status"] == status]

    # Text search
    query = params.get("query", "").strip().lower()
    if query:
        df_f = df_f[df_f["search_blob"].str.contains(query, na=False)]

    return df_f.reset_index(drop=True)


def render_banner():
    with st.container():
        st.markdown(
            """
            <div class="hanvion-banner">
                <div style="display:flex; justify-content:space-between; gap:18px; align-items:flex-start;">
                    <div style="flex:3;">
                        <div style="font-size:13px; letter-spacing:0.08em; text-transform:uppercase; opacity:0.85;">
                            Hanvion Health · Clinical Navigation
                        </div>
                        <h1 style="margin:4px 0 4px 0; font-size:30px; font-weight:800;">
                            ICD-10 Lookup Dashboard
                        </h1>
                        <p style="margin:0; font-size:14px; max-width:640px;">
                            Search ICD-10 diagnosis codes, explore related codes in the same family,
                            and generate a short, AI-assisted explanation for educational use.
                        </p>
                    </div>
                    <div style="flex:1; text-align:right; font-size:11px; opacity:0.85;">
                        <span class="hanvion-chip">Non-diagnostic • Not for billing</span><br/>
                        <span style="font-size:11px;">Always confirm with official coding sources and a qualified clinician.</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_code_card(row, show_ai: bool = True):
    """Render one ICD code card + optional AI explanation expander."""
    with st.container():
        st.markdown(
            f"""
            <div class="hanvion-card" style="margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; gap:12px;">
                    <div style="flex:3;">
                        <div class="code-pill">{row.code}</div>
                        <h3 style="margin:8px 0 2px 0; font-size:18px; font-weight:700;">
                            {row.short_description or "No short description"}
                        </h3>
                        <p class="hanvion-muted" style="font-size:13px; margin:4px 0 0 0;">
                            {row.long_description or "No long description available."}
                        </p>
                        <p style="font-size:11px; margin-top:6px; opacity:0.85;">
                            Chapter: <strong>{row.chapter or "N/A"}</strong>
                            &nbsp;·&nbsp;
                            Category: <strong>{row.category or "N/A"}</strong>
                            {f"&nbsp;·&nbsp;Status: <strong>{row.status}</strong>" if hasattr(row, "status") and row.status else ""}
                        </p>
                    </div>
                    <div style="flex:1; text-align:right; font-size:12px;">
                        <button disabled style="
                            border-radius:999px;
                            border:1px solid #e5e7eb;
                            padding:4px 10px;
                            font-size:11px;
                            background:rgba(248,250,252,0.75);
                            cursor:default;
                        ">
                            Copy code: {row.code}
                        </button>
                        <div style="font-size:11px; margin-top:6px;" class="hanvion-muted">
                            Use this code in your EHR / analytics tools as appropriate.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if show_ai:
        with st.expander("AI explanation (educational use only)", expanded=False):
            st.caption(
                "Generated by Perplexity Sonar. Not a diagnosis or billing guidance."
            )
            if st.button(
                "Learn about this condition",
                key=f"ai_{row.code}",
            ):
                with st.spinner("Asking AI for a brief explanation…"):
                    text = call_perplexity_icd_explanation(
                        code=row.code,
                        short_desc=row.short_description,
                        long_desc=row.long_description,
                        chapter=row.chapter,
                    )
                st.write(text)


def render_related_codes(df: pd.DataFrame, category: str, current_code: str):
    """Show other codes in the same 3-character category."""
    if not category:
        return

    subset = df[(df["category"] == category) & (df["code"] != current_code)]
    if subset.empty:
        return

    with st.expander("View related codes in this category"):
        for _, r in subset.iterrows():
            st.markdown(
                f"- **{r.code}** — {r.short_description or 'No short description'}"
            )


# =========================================================
# 5. MAIN APP
# =========================================================

def main():
    df = load_icd10_data()

    # Sidebar & filters
    params = render_sidebar(df)
    df_filtered = apply_filters(df, params)

    render_banner()
    st.write("")  # spacing

    # Results summary
    st.markdown(
        f"**Showing {len(df_filtered):,} of {len(df):,} codes "
        f"matching your filters.**"
    )

    # Pagination
    page_size = params["page_size"]
    total_pages = max(1, (len(df_filtered) + page_size - 1) // page_size)

    col_page, col_info = st.columns([1, 4])
    with col_page:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
        )
    with col_info:
        st.caption(f"Showing page {page} of {total_pages}")

    start = (page - 1) * page_size
    end = start + page_size
    page_df = df_filtered.iloc[start:end]

    if page_df.empty:
        st.info("No codes found. Try adjusting your search or filters.")
        return

    # Render each code card
    for _, row in page_df.iterrows():
        render_code_card(row)
        render_related_codes(df_filtered, row.category, row.code)


if __name__ == "__main__":
    main()
