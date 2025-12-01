# ============================================================
# HANVION HEALTH • ICD-10 EXPLORER  (Clean UI + No HTML showing)
# Dataset used: section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx
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

# Hanvion style (no HTML leakage)
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
# LOAD DATASET (AUTO-MAPPING ANY COLUMN NAMES)
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
# SEVERITY HEURISTIC
# ============================================================
def get_severity(code, desc):
    text = f"{code} {desc}".lower()
    if "coma" in text or "shock" in text or "respiratory failure" in text:
        return "Severe", "🔴🔴"
    if "acute" in text or "exacerbation" in text:
        return "Moderate", "🟡🟡"
    return "Mild", "🟢🟢"


# ============================================================
# OFFLINE AI EXPLANATIONS (NO API NEEDED)
# ============================================================
def explain_basic(code, desc):
    return f"**{code}** classifies the condition:\n\n{desc}\n\nThis helps clinicians document and communicate the diagnosis."

def explain_clinical(code, desc):
    return f"Clinically, **{code}** groups similar conditions for evaluation, analytics, and follow-up planning."

def explain_patient(code, desc):
    return f"This code represents the condition: **{desc}**.\nDoctors use this for medical records — not a treatment plan."

def explain_pathway(code, desc):
    return "Typical educational clinical pathway:\n- Initial evaluation\n- Relevant labs/imaging\n- Severity documentation\n- Follow-up monitoring"


# ============================================================
# PDF EXPORT FEATURE
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
    sev_label, sev_icon = get_severity(row["code"], row["description"])
    text(f"Severity: {sev_icon} {sev_label}")
    text("Educational only — Not medical advice.", 10, False, 40)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ============================================================
# RENDER CARD (PURE STREAMLIT — NO HTML LEAKING)
# ============================================================
def show_icd_card(row):
    code = row["code"]
    desc = row["description"]
    longd = row["long_description"]

    sev_label, sev_icon = get_severity(code, desc)

    with st.container():
        st.markdown('<div class="han-card">', unsafe_allow_html=True)

        st.markdown(f"<span class='code-badge'>{code}</span>", unsafe_allow_html=True)
        st.markdown(f"### {desc}")
        st.markdown(f"{longd}")

        st.markdown(
            f"<p class='han-muted'>Chapter: {row['chapter']} · Category: {row['category']}</p>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<p class='han-muted'>Severity: {sev_icon} {sev_label}</p>",
            unsafe_allow_html=True
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # AI sections
    with st.expander("🧠 AI Quick Summary"):
        st.write(explain_basic(code, desc))

    with st.expander("📚 Clinical Explanation"):
        st.write(explain_clinical(code, desc))

    with st.expander("❤️ Patient-Friendly Explanation"):
        st.write(explain_patient(code, desc))

    with st.expander("🩺 Educational Clinical Pathway"):
        st.write(explain_pathway(code, desc))

    # Related codes
    with st.expander("Related ICD-10 Codes"):
        prefix = code[:3]
        rel = df[df["code"].str.startswith(prefix)]
        for _, r in rel.iterrows():
            if r["code"] != code:
                st.write(f"{r['code']} — {r['description']}")

    # PDF EXPORT
    pdf = build_pdf(row)
    st.download_button(
        "Download PDF Summary",
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
per_page = st.number_input("Results per page", min_value=5, max_value=50, value=20)

# Filtering
if query:
    q = query.lower()
    results = df[
        df["code"].str.lower().str.contains(q) |
        df["description"].str.lower().str.contains(q)
    ]
else:
    results = df

total = len(results)
page = st.number_input("Page", min_value=1, max_value=max(1, total // per_page + 1), value=1)

start = (page - 1) * per_page
end = start + per_page
subset = results.iloc[start:end]

st.caption(f"Showing {start+1}–{min(end, total)} of {total} results")

# Render
for _, row in subset.iterrows():
    show_icd_card(row)
