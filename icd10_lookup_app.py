# =========================================================
# Hanvion Health – ICD-10 Lookup App (Premium Theme)
# =========================================================

import streamlit as st
import pandas as pd

# -----------------------------------------
# PAGE CONFIG
# -----------------------------------------
st.set_page_config(
    page_title="ICD-10 Lookup | Hanvion Health",
    page_icon="🩺",
    layout="wide"
)

# -----------------------------------------
# PREMIUM HANVION THEME (NO LOGO NEEDED)
# -----------------------------------------
st.markdown("""
<style>

body, input, textarea {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial;
}

/* Header Gradient */
.hanvion-header {
    background: linear-gradient(90deg, #8A0E1C, #B3122F, #8A0E1C);
    padding: 26px;
    border-radius: 12px;
    margin-bottom: 20px;
}
.hanvion-header h1 {
    color: white;
    font-weight: 800;
    margin: 0;
}
.hanvion-header p {
    color: #f2dede;
    margin: 0;
    font-size: 15px;
}

/* Cards */
.hanvion-card {
    background: #ffffff;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e5e5;
    box-shadow: 0 4px 14px rgba(0,0,0,0.05);
    margin-bottom: 14px;
}

/* Dark Mode Support */
@media (prefers-color-scheme: dark) {
    .hanvion-card {
        background: #1e293b;
        border: 1px solid #334155;
    }
    .hanvion-header {
        background: linear-gradient(90deg, #4b0b12, #7a0e20, #4b0b12);
    }
    .hanvion-header p {
        color: #ffcdd2;
    }
}

/* Prevent text selection on headings */
.noselect {
    user-select: none;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------------------
# HEADER
# -----------------------------------------
st.markdown("""
<div class="hanvion-header noselect">
    <h1>ICD-10 Lookup Tool</h1>
    <p>Fast Search • Clinical Coding • Hanvion Health</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------
# LOAD ICD-10 DATA
# -----------------------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns={"icd10code": "code", "icd10description": "description"}, inplace=True)
    return df

try:
    df = load_icd10()
except Exception as e:
    st.error("❌ Could not load dataset. Please upload the ICD-10 Excel file.")
    st.stop()

# -----------------------------------------
# SEARCH UI
# -----------------------------------------
st.markdown('<div class="hanvion-card">', unsafe_allow_html=True)
search = st.text_input("🔎 Search ICD-10 Code or Description", "").strip()
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------
# FILTERING
# -----------------------------------------
if search:
    results = df[
        df["code"].str.contains(search, case=False, na=False) |
        df["description"].str.contains(search, case=False, na=False)
    ]
else:
    results = df.head(0)

# -----------------------------------------
# RESULTS
# -----------------------------------------
st.markdown('<div class="hanvion-card">', unsafe_allow_html=True)
st.markdown(f"### 🔍 Results ({len(results)})")

if len(results) > 0:
    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Type to search ICD-10 codes.")
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------
# FOOTER
# -----------------------------------------
st.markdown("""
<p style='text-align:center; font-size:12px; color:#777; margin-top:30px;' class='noselect'>
    Hanvion Health © 2025 — Clinical Coding Intelligence
</p>
""", unsafe_allow_html=True)
