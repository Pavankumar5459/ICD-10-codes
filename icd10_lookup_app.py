import streamlit as st
import pandas as pd

# Load ICD-10 dataset
file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

@st.cache_data
def load_data():
    # Try reading multiple sheets (Included + Excluded)
    try:
        included = pd.read_excel(file_path, sheet_name=0)
        excluded = pd.read_excel(file_path, sheet_name=1)

        included.columns = included.columns.str.strip()
        excluded.columns = excluded.columns.str.strip()

        included["STATUS"] = "Included"
        excluded["STATUS"] = "Excluded"

        df = pd.concat([included, excluded], ignore_index=True)

    except:
        # If only one sheet exists
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["STATUS"] = "Included"

    return df

df = load_data()

# Title
st.title("🔍 ICD-10 Search Dashboard (Included + Excluded Codes)")
st.write("Search ICD-10 Diagnosis Codes, Descriptions, and Categories (CMS 2026 Update)")

# Filter for Included / Excluded / All
code_type = st.selectbox(
    "Choose ICD-10 Code Category:",
    ["All Codes", "Included Only", "Excluded Only"]
)

if code_type == "Included Only":
    filtered_df = df[df["STATUS"] == "Included"]
elif code_type == "Excluded Only":
    filtered_df = df[df["STATUS"] == "Excluded"]
else:
    filtered_df = df

# Search
search = st.text_input("Search by ICD-10 Code or Diagnosis:", "")

# Apply filtering + search
if search:
    search_lower = search.lower()
    results = filtered_df[
        filtered_df.apply(
            lambda row: search_lower in row.astype(str).str.lower().to_string(),
            axis=1
        )
    ]

    if results.empty:
        st.warning("No matching ICD-10 codes found.")
    else:
        st.success(f"Found {len(results)} result(s):")
        st.dataframe(results, use_container_width=True)
else:
    st.info("Type something above to search ICD-10 codes.")
    st.dataframe(filtered_df.head(25), use_container_width=True)
