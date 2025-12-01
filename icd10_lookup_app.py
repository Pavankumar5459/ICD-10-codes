# ============================================================
# Hanvion Health – ICD-10 Explorer (Final + Feature X PDF Export)
# Dataset used: section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx
# ============================================================

import streamlit as st
import pandas as pd
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
    page_icon="💠"
)


# ============================================================
# 2. HINVION CSS THEME
# ============================================================
st.markdown("""
<style>
.icd-card {
    background: #faf5ff;
    border: 1px solid #e9d8fd;
    border-radius: 14px;
    padding: 18px;
    margin-top: 18px;
}
.code-badge {
    background: #6b46c1;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 13px;
    display: inline-block;
    margin-bottom: 6px;
}
.muted {
    color: #6b7280;
    font-size: 13px;
}
.severity-pill {
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. LOAD ICD DATA (AUTO-Detect Columns)
# ============================================================
@st.cache_data
def load_icd10():
    file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"
    df = pd.read_excel(file_path, dtype=str).fillna("")

    # Normalize → dynamic column matching
    col_map = {"code": "", "description": "", "long_description": "", "chapter": "", "category": ""}

    for col in df.columns:
        c = col.lower()
        if ("code" in c and "icd" in c) or c == "code":
            col_map["code"] = col
        elif "short" in c or ("desc" in c and "long" not in c):
            col_map["description"] = col
        elif "long" in c:
            col_map["long_description"] = col
        elif "chapter" in c:
            col_map["chapter"] = col
        elif "category" in c or "group" in c:
            col_map["category"] = col

    # Build unified DataFrame
    df_clean = pd.DataFrame()
    df_clean["code"] = df.get(col_map["code"], "")
    df_clean["description"] = df.get(col_map["description"], "")
    df_clean["long_description"] = df.get(col_map["long_description"], "")
    df_clean["chapter"] = df.get(col_map["chapter"], "")
    df_clean["category"] = df.get(col_map["category"], "")

    return df_clean


df = load_icd10()


# ============================================================
# 4. Severity Heuristic
# ============================================================
def severity(code, desc):
    text = (code + " " + desc).lower()

    if any(w in text for w in ["coma", "respiratory failure", "shock", "sepsis"]):
        return "Severe", "🔴🔴"
    if any(w in text for w in ["uncontrolled", "acute", "exacerbation"]):
        return "Moderate", "🟡🟡"
    return "Mild", "🟢🟢"


# ============================================================
# 5. AI Educational Explanation (Offline)
# ============================================================
def ai_quick_summary(code, desc):
    return f"""
### Quick Summary for {code}

**{desc}** is a medically recognized condition classified under ICD-10.  
This code standardizes communication across hospitals, insurers, and EHR systems.
"""


def ai_clinical_summary(code, desc):
    return f"""
### Clinical Overview

- Helps clinicians document the condition clearly  
- Used to group diseases in analytics & risk scoring  
- Supports decision-making across healthcare teams  
- Not a treatment plan — purely classification  
"""


def ai_patient_friendly(code, desc):
    return f"""
### Patient-Friendly Explanation

This code (**{code}**) represents:

**{desc}**

Doctors use this label to document your condition in medical records.  
It helps them plan care, track symptoms, and share information with other clinicians.

This is educational — always talk to your doctor for personal advice.
"""


def ai_clinical_pathway(code, desc):
    return f"""
### Clinical Pathway (Educational Only)

Typical steps may include:

- Initial evaluation based on symptoms  
- Relevant labs or imaging if required  
- Documenting whether severity is mild/moderate/severe  
- Follow-up planning  
- Monitoring for complications  

This varies by patient — not medical advice.
"""


# ============================================================
# 6. PDF GENERATOR (Feature X)
# ============================================================
def build_pdf(row):
    """Creates a 1-page PDF summary for the ICD code."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x = 50
    y = height - 50

    def put(text, size=12, bold=False, space=20):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(x, y, text)
        y -= space

    put("Hanvion Health – ICD-10 Summary", 16, True, 30)
    put(f"Code: {row['code']}", 14, True)
    put(f"Description: {row['description']}", 12)
    put(f"Details: {row['long_description']}", 12)
    put(f"Chapter: {row['chapter']}   Category: {row['category']}", 11)
    put("Severity (educational):", 12, True)
    
    sev_label, sev_icon = severity(row["code"], row["description"])
    put(f"{sev_icon} {sev_label}", 12)

    put("Educational Only — Not for billing or diagnosis.", 10, False, 40)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
# 7. Render ICD Card
# ============================================================
def render_card(row):
    code = row["code"]
    desc = row["description"]
    longd = row["long_description"]
    chapter = row["chapter"] or "N/A"
    category = row["category"] or "N/A"

    sev_label, sev_icon = severity(code, desc)

    # MAIN CARD UI (unchanged)
    st.markdown(f"""
    <div class="icd-card">
        <div class="code-badge">{code}</div>

        <h3>{desc}</h3>
        <p style="font-size:14px;">{longd}</p>

        <p class="muted">Chapter: {chapter} · Category: {category}</p>

        <p class="muted">
            Severity: <span class="severity-pill">{sev_icon} {sev_label}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ===== ADD-ON EXPANDERS =====
    with st.expander("🧠 AI Quick Summary"):
        st.markdown(ai_quick_summary(code, desc))

    with st.expander("📚 Clinical Explanation"):
        st.markdown(ai_clinical_summary(code, desc))

    with st.expander("❤️ Patient-Friendly Explanation"):
        st.markdown(ai_patient_friendly(code, desc))

    with st.expander("🩺 Clinical Pathway"):
        st.markdown(ai_clinical_pathway(code, desc))

    with st.expander("Related ICD-10 Codes"):
        prefix = code[:3]
        related = df[df["code"].str.startswith(prefix)]
        for _, r in related.iterrows():
            if r["code"] != code:
                st.write(f"**{r['code']}** — {r['description']}")

    # ===== PDF EXPORT BUTTON (Feature X) =====
    pdf_file = build_pdf(row)
    st.download_button(
        label="Download PDF Summary",
        data=pdf_file,
        file_name=f"{code}_hanvion_summary.pdf",
        mime="application/pdf"
    )


# ============================================================
# 8. MAIN APP LOGIC
# ============================================================
st.title("Hanvion Health · ICD-10 Explorer")
st.caption("Search ICD codes, view clinical context, and generate summaries.")

query = st.text_input("Search by ICD code or diagnosis")
per_page = st.number_input("Results per page", 5, 50, 20)

# FILTER LOGIC
if query:
    q = query.lower()
    results = df[df.apply(lambda r: q in r["code"].lower() or q in r["description"].lower(), axis=1)]
else:
    results = df

total = len(results)
page = st.number_input("Page", 1, max(1, (total - 1) // per_page + 1), 1)

start = (page - 1) * per_page
end = start + per_page
subset = results.iloc[start:end]

st.caption(f"Showing {start+1}–{min(end, total)} of {total} results")

# Render Results
for _, row in subset.iterrows():
    render_card(row)

# END OF FILE
