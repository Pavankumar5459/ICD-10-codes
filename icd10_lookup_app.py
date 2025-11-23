import streamlit as st
import pandas as pd

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="ICD-10 Lookup | Hanvion Health",
    page_icon="🩺",
    layout="wide"
)

# -----------------------------
# Custom CSS (Hanvion Health Branding)
# -----------------------------
st.markdown(
    """
    <style>
    .main {
        background-color: #F5F7FB;
    }
    .hh-header {
        background: linear-gradient(90deg, #003262, #0369A1);
        padding: 22px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.18);
    }
    .hh-title {
        font-size: 36px;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .hh-subtitle {
        font-size: 16px;
        opacity: 0.9;
        font-weight: 400;
    }
    .hh-tagline {
        margin-top: 10px;
        font-size: 13px;
        opacity: 0.9;
    }
    .hh-brand-pill {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 999px;
        background-color: rgba(255,255,255,0.18);
        font-size: 12px;
    }
    .hh-link a {
        color: #E0F2FE;
        text-decoration: underline;
        font-size: 13px;
    }
    .hh-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        border: 1px solid #E0E7FF;
    }
    .hh-card-title {
        font-size: 17px;
        font-weight: 700;
        color: #003262;
        margin-bottom: 10px;
    }
    .hh-footer {
        text-align: center;
        margin-top: 40px;
        padding: 15px;
        color: #737373;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Load ICD-10 dataset
# -----------------------------
file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

@st.cache_data
def load_data():
    try:
        included = pd.read_excel(file_path, sheet_name=0)
        excluded = pd.read_excel(file_path, sheet_name=1)

        included.columns = included.columns.str.strip()
        excluded.columns = excluded.columns.str.strip()

        included["STATUS"] = "Included"
        excluded["STATUS"] = "Excluded"

        df = pd.concat([included, excluded], ignore_index=True)

    except:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["STATUS"] = "Included"

    return df

df = load_data()

# -----------------------------
# Header (Hanvion Health Style)
# -----------------------------
st.markdown(
    """
    <div class="hh-header">
        <div class="hh-title">ICD-10 Lookup Dashboard</div>
        <div class="hh-subtitle">
            Search Included & Excluded ICD-10 Codes (CMS 2026 Update) with Hanvion Health's Intelligent Lookup Tool.
        </div>
        <div class="hh-tagline">
            <span class="hh-brand-pill">Powered by Hanvion Health</span><br>
            <span class="hh-link">Visit: <a href="https://hanvionhealth.com" target="_blank">hanvionhealth.com</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Layout: Filters and Search
# -----------------------------
col1, col2 = st.columns([1.2, 3])

# FILTERS CARD
with col1:
    st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
    st.markdown("<div class='hh-card-title'>Select Code Type</div>", unsafe_allow_html=True)

    code_type = st.selectbox(
        "Choose ICD-10 Code Category",
        ["All Codes", "Included Only", "Excluded Only"]
    )

    # Description for each category
    if code_type == "Included Only":
        st.info("✔ **Included ICD-10 Codes**: Valid for CMS Section 111 Mandatory Reporting. Accepted by CMS.")
    elif code_type == "Excluded Only":
        st.warning("⚠ **Excluded ICD-10 Codes**: Valid medical descriptions but **NOT accepted by CMS** for Section 111 reporting.")
    else:
        st.info("Showing all codes from CMS ICD-10 dataset (Included + Excluded).")

    st.markdown("</div>", unsafe_allow_html=True)

# SEARCH CARD
with col2:
    st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
    st.markdown("<div class='hh-card-title'>Search ICD-10 Code or Diagnosis</div>", unsafe_allow_html=True)

    search = st.text_input(
        "Search Diagnosis Name or ICD-10 Code:",
        placeholder="Example: J45, asthma, fracture, diabetes..."
    )

    st.markdown("</div>", unsafe_allow_html=True)

# Filter based on Included/Excluded
if code_type == "Included Only":
    filtered_df = df[df["STATUS"] == "Included"]
elif code_type == "Excluded Only":
    filtered_df = df[df["STATUS"] == "Excluded"]
else:
    filtered_df = df

# -----------------------------
# Results Section
# -----------------------------
st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
st.markdown("<div class='hh-card-title'>Results</div>", unsafe_allow_html=True)

if search:
    search_lower = search.lower()
    results = filtered_df[
        filtered_df.apply(lambda row: search_lower in row.astype(str).str.lower().to_string(), axis=1)
    ]

    if results.empty:
        st.error("❌ No ICD-10 codes found for your search.")
    else:
        st.success(f"✨ Found {len(results)} matching result(s)")
        st.dataframe(results, use_container_width=True)
else:
    st.info("Start typing a keyword to search ICD-10 codes. Showing the first 25 codes below.")
    st.dataframe(filtered_df.head(25), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Footer
# -----------------------------
st.markdown(
    """
    <div class='hh-footer'>
        © 2025 Hanvion Health • ICD-10 Lookup Platform • CMS 2026 ICD-10 Data • All Rights Reserved.
    </div>
    """,
    unsafe_allow_html=True
)
