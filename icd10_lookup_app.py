import streamlit as st
import pandas as pd
import re

# ================================================================
# 1. PAGE CONFIG
# ================================================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
    page_icon="💠"
)

# ================================================================
# 2. HINVION THEME CSS (NO HTML LEAKING)
# ================================================================
st.markdown("""
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial;
}

h1, h2, h3, h4 {
    user-select: none;
}

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

# ================================================================
# 3. LOAD DATA (AUTO MAP YOUR RANDOM COLUMN NAMES)
# ================================================================
@st.cache_data
def load_icd10():
    xfile = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

    df = pd.read_excel(xfile, dtype=str).fillna("")

    # Automatic flexible mapping
    col_map = {
        "code": None,
        "description": None,
        "long_description": None,
        "chapter": None,
        "category": None
    }

    for col in df.columns:
        c = col.lower()
        if ("code" in c and "icd" in c) or c.startswith("code"):
            col_map["code"] = col
        elif "short" in c or "desc" in c:
            col_map["description"] = col
        elif "long" in c and "desc" in c:
            col_map["long_description"] = col
        elif "chapter" in c:
            col_map["chapter"] = col
        elif "category" in c or "group" in c:
            col_map["category"] = col

    # Build normalized dataset
    df_clean = pd.DataFrame()
    df_clean["code"] = df[col_map["code"]]
    df_clean["description"] = df[col_map["description"]]
    df_clean["long_description"] = df[col_map["long_description"]]
    df_clean["chapter"] = df[col_map["chapter"]]
    df_clean["category"] = df[col_map["category"]]

    return df_clean


df = load_icd10()

# ================================================================
# 4. SEVERITY HEURISTIC
# ================================================================
def severity(code, desc):
    text = (code + " " + desc).lower()

    if any(k in text for k in ["coma", "sepsis", "shock", "respiratory failure"]):
        return "Severe", "🔴🔴"
    if any(k in text for k in ["diabetes", "asthma", "pneumonia", "fracture"]):
        return "Moderate", "🟡🟡"
    return "Mild", "🟢🟢"

# ================================================================
# 5. AI EXPLANATION STUB (SAFE — DOES NOT REQUIRE API KEY)
#    You can replace this with Perplexity API later.
# ================================================================
def ai_explain(code, desc):
    text = f"""
### Educational explanation for ICD-10 code **{code}**

**Condition:** {desc}

This condition is part of the ICD-10 classification system for healthcare documentation.  
It is typically used by clinicians, coders, and health analysts to:

- Identify the specific disease or condition  
- Support billing and insurance workflows  
- Enable research, analytics, and epidemiology  
- Standardize communication across EHR systems  

For patient-friendly educational information, consult a licensed clinician.

*AI educational mode only — not medical advice.*
    """
    return text

# ================================================================
# 6. ICD-10 CARD RENDERING (HTML FIXED)
# ================================================================
def render_card(row):
    code = row["code"]
    desc = row["description"]
    longd = row["long_description"]
    chapter = row["chapter"] or "N/A"
    category = row["category"] or "N/A"

    sev_label, sev_bar = severity(code, desc)

    html = f"""
    <div class="icd-card">
        <div class="code-badge">{code}</div>

        <h3>{desc}</h3>
        <p style="font-size:14px;">{longd}</p>

        <p class="muted">Chapter: {chapter} · Category: {category}</p>

        <p class="muted" style="margin-top:4px;">
            Severity (heuristic):
            <span class="severity-pill">{sev_bar} {sev_label}</span>
        </p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # AI Expander
    with st.expander(f"AI explanation for {code}"):
        st.markdown(ai_explain(code, desc))

    # Related codes
    prefix = code[:3]
    with st.expander("Related ICD-10 codes in this family"):
        related = df[df["code"].str.startswith(prefix)]
        for _, r in related.iterrows():
            if r["code"] != code:
                st.write(f"**{r['code']}** — {r['description']}")

# ================================================================
# 7. SEARCH + UI
# ================================================================
st.title("Hanvion Health · ICD-10 Explorer")
st.write("Search ICD-10 codes, view clinical context, and learn with AI (educational).")

query = st.text_input("Search by code or diagnosis", "")
results_per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 9999, 1)

# FILTER
if query.strip():
    q = query.lower()
    mask = df.apply(lambda r: q in r["code"].lower() or q in r["description"].lower(), axis=1)
    results = df[mask]
else:
    results = df

# PAGINATION
total = len(results)
start = (page - 1) * results_per_page
end = start + results_per_page
subset = results.iloc[start:end]

st.caption(f"Showing {start+1}–{min(end, total)} of {total} codes")

for _, row in subset.iterrows():
    render_card(row)

