import streamlit as st
import pandas as pd

# =========================================================
# HANVION THEME CSS
# =========================================================
HANVION_CSS = """
<style>
.block-container {
    max-width: 1120px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", Segoe UI, Roboto, sans-serif;
}

.hanvion-hero {
    background: linear-gradient(180deg, #9a0028 0%, #7b001f 40%, #4f0016 100%);
    border-radius: 18px;
    padding: 28px 34px;
    color: white;
    box-shadow: 0 18px 40px rgba(0,0,0,0.25);
    margin-bottom: 24px;
}

.hanvion-title {
    font-size: 44px;
    font-weight: 800;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    margin-bottom: 0;
}

.hanvion-subtitle {
    font-size: 16px;
    font-weight: 400;
    opacity: 0.95;
    letter-spacing: 0.32em;
    margin-top: 2px;
}

.hanvion-chip {
    display: inline-block;
    margin-top: 16px;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.55);
    font-size: 11px;
    text-transform: uppercase;
    opacity: 0.9;
}

.code-box {
    background: #faf5ff;
    border-radius: 12px;
    padding: 14px;
    border: 1px solid #e5d4ff;
    margin-bottom: 14px;
}

.result-title {
    font-size: 22px;
    font-weight: 600;
    margin-top: 4px;
}

.result-subtitle {
    font-size: 15px;
    opacity: 0.8;
}

[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e5e7eb;
}
</style>
"""

def inject_css():
    st.markdown(HANVION_CSS, unsafe_allow_html=True)


# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx", dtype=str).fillna("")
    df = df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_description",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_description",
        "NF EXCL": "nf_excl"
    })
    return df


# =========================================================
# MAIN APP
# =========================================================
def main():

    inject_css()

    # ----------------------------------------
    # Hanvion Header Banner
    # ----------------------------------------
    st.markdown(
        """
        <div class="hanvion-hero">
            <div class="hanvion-title">HANVION</div>
            <div class="hanvion-subtitle">HEALTH</div>
            <div class="hanvion-chip">ICD-10 Explorer • Educational Lookup</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("Search ICD-10 codes using the official CMS dataset. Educational use only — not for billing or diagnosis.")

    df = load_icd10()

    # ----------------------------------------
    # Search Input
    # ----------------------------------------
    query = st.text_input("Search ICD-10 code or condition", placeholder="Example: asthma, diabetes, J45, E11")

    if not query.strip():
        st.info("Start typing a condition or ICD-10 code above to see results.")
        return

    q = query.lower()

    filtered = df[
        df["code"].str.lower().str.contains(q) |
        df["short_description"].str.lower().str.contains(q) |
        df["long_description"].str.lower().str.contains(q)
    ]

    # ----------------------------------------
    # Pagination
    # ----------------------------------------
    page_size = st.number_input("Results per page", min_value=5, max_value=50, value=20)
    page = st.number_input("Page", min_value=1, value=1)

    start = (page - 1) * page_size
    end = start + page_size
    results = filtered.iloc[start:end]

    st.caption(f"Showing {len(results)} of {len(filtered)} results.")

    # ----------------------------------------
    # Display Results
    # ----------------------------------------
    for _, row in results.iterrows():
        st.markdown(
            f"""
            <div class='code-box'>
                <div style="font-size:14px; background:#6b21a8; color:white; 
                display:inline-block; padding:3px 10px; border-radius:6px; margin-bottom:10px;">
                    {row['code']}
                </div>

                <div class="result-title">{row['short_description']}</div>
                <div class="result-subtitle">{row['long_description']}</div>

                <p style="font-size:13px; margin-top:6px; opacity:0.7;">
                    NF Exclusions: {row['nf_excl'] if row['nf_excl'] else 'None'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# RUN APP
# =========================================================
if __name__ == "__main__":
    main()
