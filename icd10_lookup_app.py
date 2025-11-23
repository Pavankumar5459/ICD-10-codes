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
# Custom CSS - Hanvion-style Theme
# -----------------------------
st.markdown(
    """
    <style>
    .main {
        background-color: #f5f7fb;
    }
    .hh-header {
        background: linear-gradient(90deg, #003262, #0369A1);
        padding: 18px 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    }
    .hh-title {
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .hh-subtitle {
        font-size: 15px;
        opacity: 0.9;
    }
    .hh-tagline {
        margin-top: 8px;
        font-size: 13px;
        opacity: 0.9;
    }
    .hh-card {
        background-color: #ffffff;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        margin-bottom: 12px;
        border: 1px solid #e0e7ff;
    }
    .hh-card-title {
        font-size: 16px;
        font-weight: 600;
        color: #003262;
        margin-bottom: 10px;
    }
    .hh-footer {
        color: #7b7b7b;
        text-align: center;
        padding-top: 32px;
        font-size: 13px;
    }
    .hh-brand-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        background-color: rgba(255,255,255,0.16);
        font-size: 12px;
        margin-top: 4px;
    }
    .hh-link a {
        color: #e0f2fe;
        text-decoration: underline;
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

    except Exception:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["STATUS"] = "Included"

    return df

df = load_data()

# -----------------------------
# Header - Hanvion Health Banner
# -----------------------------
st.markdown(
    """
    <div class="hh-header">
        <div class="hh-title">ICD-10 Lookup Dashboard</div>
        <div class="hh-subtitle">
            A clinical coding search tool to explore Included and Excluded ICD-10-CM codes (CMS 2026 update).
        </div>
        <div class="hh-tagline">
            <span class="hh-brand-pill">Powered by Hanvion Health</span>
            <br/>
            <span class="hh-link">
                Visit: <a href="https://hanvionhealth.com" target="_blank">hanvionhealth.com</a>
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Layout: Filters + Results
# -----------------------------
filter_col, search_col = st.columns([1, 3])

with filter_col:
    st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
    st.markdown("<div class='hh-card-title'>Filter ICD-10 Category</div>", unsafe_allow_html=True)

    code_type = st.selectbox(
        "Code Type",
        ["All Codes", "Included Only", "Excluded Only"],
        help="Choose whether to search all ICD-10 codes, or only those included/excluded for CMS reporting."
    )

    if code_type == "Included Only":
        filtered_df = df[df["STATUS"] == "Included"]
    elif code_type == "Excluded Only":
        filtered_df = df[df["STATUS"] == "Excluded"]
    else:
        filtered_df = df

    st.markdown("</div>", unsafe_allow_html=True)

with search_col:
    st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
    st.markdown("<div class='hh-card-title'>Search ICD-10 Codes</div>", unsafe_allow_html=True)

    search = st.text_input(
        "Search by Code or Diagnosis Text",
        placeholder="Example: F32, depression, fracture, diabetes...",
    )

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Results Section
# -----------------------------
st.markdown("<div class='hh-card'>", unsafe_allow_html=True)
st.markdown("<div class='hh-card-title'>Search Results</div>", unsafe_allow_html=True)

if search:
    search_lower = search.lower()

    results = filtered_df[
        filtered_df.apply(
            lambda row: search_lower in row.astype(str).str.lower().to_string(),
            axis=1
        )
    ]

    if results.empty:
        st.warning("No matching ICD-10 codes found for your search.")
    else:
        st.success(f"Found {len(results)} matching result(s).")
        st.dataframe(results, use_container_width=True)
else:
    st.info("Start typing above to search ICD-10 codes. Showing a sample preview below.")
    st.dataframe(filtered_df.head(25), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Footer
# -----------------------------
st.markdown(
    """
    <div class='hh-footer'>
        © 2025 Hanvion Health • ICD-10 Lookup Tool • For informational and educational use only.
    </div>
    """,
    unsafe_allow_html=True
)
