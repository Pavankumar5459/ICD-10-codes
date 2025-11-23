import streamlit as st
import pandas as pd

# Load ICD-10 dataset
file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

@st.cache_data
def load_data():
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    return df

df = load_data()

st.title("🔍 ICD-10 Search Dashboard")
st.write("Search ICD-10 Codes, Disease Names, and Categories")

search = st.text_input("Search by ICD-10 Code or Disease Name:", "")

if search:
    search_lower = search.lower()
    results = df[df.apply(lambda row: search_lower in row.astype(str).str.lower().to_string(), axis=1)]
    if results.empty:
        st.warning("No matching results found.")
    else:
        st.success(f"Found {len(results)} matching results:")
        st.dataframe(results, use_container_width=True)
else:
    st.info("Type something above to search ICD-10 codes.")
    st.dataframe(df.head(20), use_container_width=True)
