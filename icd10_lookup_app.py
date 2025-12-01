# ============================================================
# HANVION HEALTH • ICD-10 EXPLORER  (Clean, No Emojis, No Auto Results)
# ============================================================

import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Hanvion Health • ICD-10 Explorer",
    layout="wide",
    page_icon="💠"
)

# Hanvion theme
st.markdown("""
<style>
.han-card {
    background: #faf5ff;
    border: 1px solid #e9d8fd;
    padding: 20px;
    border-radius: 15px;
    margin-top: 18px;
}
.code-badge {
    background: #6b46c1;
    color: white;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
}
.han-muted {
    color:#6b7280; 
    font-size:13px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# LOAD DATASET (any column names supported)
# ============================================================
@st.cache_data
def load_data():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    df.columns = [c.lower().strip() for c in df.columns]

    def pick(*keys):
        for k in keys:
            for col in df.columns:
                if k in col:
                    return col
        return None

    col_code = pick("code", "icd")
    col_desc = pick("desc", "short")
    col_long = pick("long")
    col_chapter = pick("chapter")
    col_cat = pick("category", "group")

    out = pd.DataFrame()
    out["code"] = df.get(col_code, "")
    out["description"] = df.get(col_desc, "")
    out["long_description"] = df.get(col_long, "")
    out["chapter"] = df.get(col_chapter, "N/A")
    out["category"] = df.get(col_cat, "N/A")
    return out

df = load_data()


# ============================================================
# PDF EXPORT
# ============================================================
def build_pdf(row):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 50

    def text(t, size=12, bold=False, space=20):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(40, y, t)
        y -= space

    text("Hanvion Health – ICD-10 Summary", 16, True, 30)
    text(f"Code: {row['code']}", 14, True)
    text(f"Description: {row['description']}")
    text(f"Details: {row['long_description']}")
    text(f"Chapter: {row['chapter']}   Category: {row['category']}")
    text("Educational use only.", 10, False, 40)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ============================================================
# RENDER ICD CARD (NO EMOJIS)
# ============================================================
def show_icd_card(row):
    code = row["code"]
    desc = row["description"]
    long_desc = row["long_description"]

    st.markdown('<div class="han-card">', unsafe_allow_html=True)

    st.markdown(f"<span class='code-badge'>{code}</span>", unsafe_allow_html=True)
    st.markdown(f"### {desc}")
    st.markdown(long_desc)

    st.markdown(
        f"<p class='han-muted'>Chapter: {row['chapter']} · Category: {row['category']}</p>",
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Explanation sections
    with st.expander("Clinical Explanation"):
        st.write(f"{code} is used for documentation and classification of: {desc}")

    with st.expander("Patient-Friendly Summary"):
        st.write(f"This ICD-10 code describes: {desc}. This helps doctors document the condition accurately.")

    # PDF button
    pdf = build_pdf(row)
    st.download_button(
        "Download Summary as PDF",
        pdf,
        file_name=f"{code}_summary.pdf",
        mime="application/pdf"
    )


# ============================================================
# MAIN UI
# ============================================================
st.title("Hanvion Health • ICD-10 Explorer")
st.caption("Search ICD codes, view clinical context, and generate summaries.")

query = st.text_input("Search by ICD code or diagnosis")

# Do NOT show anything unless the user searches
if not query:
    st.info("Start typing to search ICD-10 codes...")
    st.stop()

# Filter results
q = query.lower()
results = df[
    df["code"].str.lower().str.contains(q) |
    df["description"].str.lower().str.contains(q)
]

if results.empty:
    st.warning("No matching ICD-10 codes found.")
    st.stop()

st.caption(f"Found {len(results)} results")

# Display results
for _, row in results.iterrows():
    show_icd_card(row)
