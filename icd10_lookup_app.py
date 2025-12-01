import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Hanvion Health – Universal UI Template (V4 Clean Medical UI)
# ---------------------------------------------------------

st.set_page_config(page_title="Hanvion Health", layout="wide")

# -----------------------------
# GLOBAL HANVION THEME CSS
# -----------------------------
st.markdown("""
<style>
body {
    background-color: #ffffff;
}

.main-title {
    font-size: 38px;
    font-weight: 700;
    color: #8B0000;
    text-align: center;
    margin-top: 20px;
    margin-bottom: 10px;
}

.subtext {
    font-size: 16px;
    color: #4a4a4a;
    text-align: center;
    margin-bottom: 30px;
}

.search-container {
    display: flex;
    justify-content: center;
    margin-top: 10px;
    margin-bottom: 25px;
}

.result-card {
    background: #F9F9FB;
    border: 1px solid #E5E5E8;
    padding: 25px;
    border-radius: 14px;
    width: 900px;
    margin: auto;
    margin-top: 20px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.04);
}

.result-title {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 6px;
}

.result-description {
    font-size: 15px;
    color: #333;
}

.section-header {
    font-size: 18px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 10px;
}

.hr-line {
    border: none;
    border-top: 1px solid #E5E5E8;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.markdown('<div class="main-title">Hanvion Health • Search Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="subtext">Search for medical information using our structured datasets.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# SEARCH BAR
# ---------------------------------------------------------
query = st.text_input("", placeholder="Search here…", label_visibility="collapsed")

# ---------------------------------------------------------
# LOGIC PLACEHOLDER (Replace for each app)
# ---------------------------------------------------------
if not query:
    st.markdown("""
        <div class="search-container">
            <div style="color:#777; font-size:16px;">
                Begin typing above to search.
            </div>
        </div>
    """, unsafe_allow_html=True)

else:
    # Example card output (replace with your logic)
    st.markdown("""
        <div class="result-card">
            <div class="result-title">Sample Result Title</div>
            <div class="result-description">
                This is where the structured medical info will appear.
            </div>
        </div>
    """, unsafe_allow_html=True)
