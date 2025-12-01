import os
import requests
import pandas as pd
import streamlit as st
from PIL import Image

# =====================================================
#  PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide"
)

# =====================================================
#  HANVION THEME CSS
# =====================================================
st.markdown(
    """
    <style>
    body, input, textarea, button, select {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Hide default code/pre blocks so raw HTML never shows */
    pre, code {
        display: none !important;
    }

    .icd-card {
        background: rgba(245,240,255,0.65);
        border: 1px solid #ede9fe;
        padding: 20px 22px;
        border-radius: 14px;
        margin-top: 18px;
    }

    .muted {
        color: #6b7280;
        font-size: 13px;
    }

    .header-box {
        display: flex;
        align-items: center;
        gap: 18px;
        margin-bottom: 6px;
    }

    .download-bar {
        margin-top: 8px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
#  LOGO SUPPORT (assets/hanvion_logo.png)
# =====================================================
def load_logo():
    try:
        path = os.path.join("assets", "hanvion_logo.png")
        if os.path.exists(path):
            return Image.open(path)
    except Exception:
        return None
    return None

logo = load_logo()

# =====================================================
#  DATA LOADER (USES YOUR EXACT COLUMN NAMES)
# =====================================================

CMS_FILE = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

@st.cache_data(show_spinner="Loading ICD-10 CMS dataset...")
def load_icd10():
    """
    Load your CMS file and map into a clean, consistent schema.

    Expected columns (exact, from your message):
    - CODE
    - SHORT DESCRIPTION (VALID ICD-10 FY2025)
    - LONG DESCRIPTION (VALID ICD-10 FY2025)
    - NF EXCL
    """
    if not os.path.exists(CMS_FILE):
        raise FileNotFoundError(
            f"Required file '{CMS_FILE}' not found in the app folder."
        )

    df_raw = pd.read_excel(CMS_FILE, dtype=str).fillna("")

    required = [
        "CODE",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)",
    ]
    for col in required:
        if col not in df_raw.columns:
            raise ValueError(f"Missing expected column in Excel: {col}")

    # Build normalized dataframe
    df = pd.DataFrame()
    df["code"] = df_raw["CODE"].astype(str).str.strip()
    df["short_description"] = df_raw["SHORT DESCRIPTION (VALID ICD-10 FY2025)"].astype(str).str.strip()
    df["long_description"] = df_raw["LONG DESCRIPTION (VALID ICD-10 FY2025)"].astype(str).str.strip()

    # NF EXCL optional
    if "NF EXCL" in df_raw.columns:
        df["nf_excl"] = df_raw["NF EXCL"].astype(str).str.strip()
    else:
        df["nf_excl"] = ""

    # Derive simple category (first 3 characters of code)
    df["category"] = df["code"].str[:3]
    df["chapter"] = "N/A"

    # Drop blank codes
    df = df[df["code"] != ""].reset_index(drop=True)

    return df

df = load_icd10()

# =====================================================
#  PERPLEXITY AI WRAPPER (sonar-pro)
# =====================================================
def get_pplx_key():
    # first try Streamlit secrets, then env var
    key = None
    try:
        key = st.secrets.get("PPLX_API_KEY", None)
    except Exception:
        key = None
    if not key:
        key = os.getenv("PPLX_API_KEY")
    return key

def ask_ai(prompt: str, mode: str = "clinical") -> str:
    """
    Calls Perplexity sonar-pro with safe educational prompts.
    mode = "clinical" or "patient"
    Returns a text string (even in error).
    """
    api_key = get_pplx_key()
    if not api_key:
        return "AI is not configured. Please add PPLX_API_KEY in Streamlit Secrets."

    if mode == "clinical":
        system_prompt = (
            "You are a medical educator writing for clinicians, students, and health data analysts. "
            "Provide structured, factual clinical explanations of ICD-10 codes. "
            "Do NOT give diagnosis, treatment, or medical advice."
        )
    else:  # patient mode
        system_prompt = (
            "You explain medical terms so that patients and families can understand. "
            "Use clear, simple language. Do NOT give treatment recommendations or medical advice."
        )

    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI request failed: {e}"

# =====================================================
#  HEADER
# =====================================================
col_logo, col_title = st.columns([1, 5])

with col_logo:
    if logo is not None:
        st.image(logo, use_column_width=False, width=120)

with col_title:
    st.markdown("### Hanvion Health · ICD-10 Explorer")
    st.markdown(
        "Search ICD-10 codes using the official CMS dataset and explore structured, "
        "educational explanations. Not for diagnosis, billing, or medical decision-making."
    )

st.markdown("---")

# =====================================================
#  SEARCH CONTROLS
# =====================================================
col_q, col_per_page = st.columns([3, 1])

with col_q:
    query = st.text_input(
        "Search by ICD-10 code or diagnosis",
        placeholder="Example: E11, diabetes, fracture, asthma",
    ).strip()

with col_per_page:
    per_page = st.number_input("Results per page", min_value=5, max_value=100, value=20, step=5)

page = st.number_input("Page", min_value=1, value=1, step=1)

# No search → no results
if not query:
    st.info("Begin typing an ICD-10 code or condition to see results.")
    st.stop()

# =====================================================
#  FILTER RESULTS
# =====================================================
q = query.lower()

mask = (
    df["code"].str.lower().str.contains(q, na=False)
    | df["short_description"].str.lower().str.contains(q, na=False)
    | df["long_description"].str.lower().str.contains(q, na=False)
)

filtered = df[mask].reset_index(drop=True)
total = len(filtered)

if total == 0:
    st.warning("No ICD-10 codes matched your search. Try a different keyword or partial code.")
    st.stop()

# =====================================================
#  EXPORT CSV (current filtered set)
# =====================================================
csv_data = filtered.to_csv(index=False).encode("utf-8")
st.markdown('<div class="download-bar">', unsafe_allow_html=True)
st.download_button(
    label="Download filtered results as CSV",
    data=csv_data,
    file_name="icd10_filtered_results.csv",
    mime="text/csv",
)
st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
#  PAGINATION
# =====================================================
start = (page - 1) * per_page
end = start + per_page
if start >= total:
    start = max(0, total - per_page)
    end = total

page_df = filtered.iloc[start:end]

st.caption(
    f"Showing {start + 1}–{min(end, total)} of {total} matching codes."
)

# =====================================================
#  DISPLAY ICD-10 CARDS
# =====================================================
for idx, row in page_df.iterrows():
    st.markdown("<div class='icd-card'>", unsafe_allow_html=True)

    code = row["code"]
    short = row["short_description"] or "(no short description)"
    long = row["long_description"] or short
    category = row["category"] or "N/A"
    chapter = row["chapter"] or "N/A"
    nf_excl = row.get("nf_excl", "")

    st.subheader(f"{code} — {short}")
    st.write(long)

    meta_text = f"Chapter: {chapter} · Category: {category}"
    if nf_excl and nf_excl.strip() not in ["", "0", "NaN", "nan"]:
        meta_text += f" · NF EXCL: {nf_excl}"

    st.markdown(f"<p class='muted'>{meta_text}</p>", unsafe_allow_html=True)

    # ---------------------- Clinical Explanation ----------------------
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Generate clinical explanation for {code}", key=f"clin_{code}"):
            prompt = (
                f"Provide a structured CLINICAL explanation for ICD-10 code {code} "
                f"({short}). Include definition, clinical context, key documentation aspects, and "
                f"typical scenarios where this code is used. Do NOT give treatment advice."
            )
            st.write(ask_ai(prompt, mode="clinical"))

    # ---------------------- Patient-Friendly Explanation ----------------------
    with st.expander("Patient-friendly explanation (educational only)"):
        if st.button(f"Generate patient explanation for {code}", key=f"pat_{code}"):
            prompt = (
                f"Explain ICD-10 code {code} ({short}) in simple language for a non-medical person. "
                f"Describe what it generally means and why a doctor might record this, but do NOT "
                f"provide medical advice or treatment instructions."
            )
            st.write(ask_ai(prompt, mode="patient"))

    # ---------------------- Compare with Another ICD Code ----------------------
    with st.expander("Compare with another ICD-10 code"):
        other_code = st.text_input(
            f"ICD-10 code to compare with {code}",
            key=f"cmp_input_{code}",
            placeholder="Example: E119",
        ).strip()

        if st.button(f"Compare {code} with {other_code or '…'}", key=f"cmp_btn_{code}"):
            if not other_code:
                st.warning("Please type another ICD-10 code to compare.")
            else:
                # Show basic info if found
                other_row = df[df["code"].str.upper() == other_code.upper()]
                if not other_row.empty:
                    o = other_row.iloc[0]
                    st.markdown(
                        f"**Found {other_code.upper()}** — {o['short_description']}"
                    )

                prompt = (
                    f"Compare ICD-10 code {code} ({short}) with ICD-10 code {other_code}. "
                    f"Explain how they differ in clinical concept, anatomical focus, and coding usage. "
                    f"Do NOT discuss treatment or give any medical advice."
                )
                st.write(ask_ai(prompt, mode="clinical"))

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
#  FOOTER
# =====================================================
st.markdown("---")
st.markdown(
    "<p class='muted'>Hanvion Health · ICD-10 Explorer is for educational and analytic purposes only. "
    "It is not intended for diagnosis, treatment, billing, or coding decisions.</p>",
    unsafe_allow_html=True,
)
