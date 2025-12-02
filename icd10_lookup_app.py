import io
import textwrap

import pandas as pd
import requests
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
)

# ==========================================
# DARK MODE TOGGLE
# ==========================================
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

dark_mode = st.sidebar.toggle("🌙 Dark mode", value=st.session_state["dark_mode"])
st.session_state["dark_mode"] = dark_mode

# ==========================================
# LIGHT + DARK CSS
# ==========================================
LIGHT_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
[data-testid="stAppViewContainer"] {
    background: #f7f9fc;
}
.hanvion-header {
    background: linear-gradient(90deg, #004c97, #0077b6);
    color: white;
    padding: 26px 30px;
    border-radius: 18px;
    margin-bottom: 20px;
    box-shadow: 0 14px 28px rgba(0,0,0,0.25);
}
.code-card {
    background: white;
    border: 1px solid #e2e8f0;
    padding: 16px 18px;
    border-radius: 14px;
    margin-top: 6px;
}
</style>
"""

DARK_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #020617;
    color: #e5e7eb;
}
.hanvion-header {
    background: radial-gradient(circle at top left, #38bdf8, #1e293b);
    color: white;
    padding: 26px 30px;
    border-radius: 18px;
    margin-bottom: 20px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.6);
}
.code-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    padding: 16px 18px;
    border-radius: 14px;
    margin-top: 6px;
}
</style>
"""

st.markdown(DARK_CSS if dark_mode else LIGHT_CSS, unsafe_allow_html=True)

# ==========================================
# LOAD CMS ICD-10 FILE (ONLY CMS — NO WHO)
# ==========================================
@st.cache_data
def load_cms_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.lower().str.strip()

    df = df.rename(columns={
        "code": "code",
        "short description (valid icd-10 fy2025)": "short_desc",
        "long description (valid icd-10 fy2025)": "long_desc"
    })

    df["nf_excl"] = df["nf excl"] if "nf excl" in df.columns else ""

    return df[["code", "short_desc", "long_desc", "nf_excl"]].sort_values("code")

df = load_cms_icd10()

# ==========================================
# PERPLEXITY AI (SONAR-PRO) — NO CITATIONS
# ==========================================
def perplexity_chat(system_prompt, user_prompt):
    api_key = st.secrets.get("PPLX_API_KEY")
    if not api_key:
        return None, "Missing PPLX_API_KEY in secrets."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 600
    }

    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions",
                             json=payload, headers=headers, timeout=25)

        if resp.status_code != 200:
            return None, f"AI HTTP {resp.status_code}: {resp.text[:300]}"

        data = resp.json()

        # Modern format
        if "output_text" in data:
            return data["output_text"], None
        if "response" in data:
            return data["response"], None

        # Legacy fallback
        if "choices" in data and data["choices"]:
            msg = data["choices"][0].get("message", {})
            content = msg.get("content")
            return content, None

        return None, f"Unexpected AI response: {data}"
    except Exception as e:
        return None, f"AI Error: {e}"

# Patient friendly summary
@st.cache_data(show_spinner=False)
def get_patient_summary(code, short_desc, long_desc):
    system = (
        "Explain medical information in clear, simple language. "
        "NEVER include citations, numbers in brackets, or sources like [1] [2] (1) etc. "
        "Do not provide medical advice."
    )
    user = f"""
Explain ICD-10 code {code} in simple language.

Short: {short_desc}
Long: {long_desc}

Explain:
- What this condition means
- Common symptoms
- When people usually talk to a doctor
(No citations, no bracket numbers.)
"""
    return perplexity_chat(system, user)

# Clinical summary
@st.cache_data(show_spinner=False)
def get_clinical_summary(code, short_desc, long_desc):
    system = (
        "You explain ICD-10 codes for clinicians. "
        "Absolutely no citations or bracket numbers. "
        "Do not provide treatment advice."
    )
    user = f"""
Provide a clinical explanation for ICD-10 code {code}.

Short: {short_desc}
Long: {long_desc}

Include:
- Clinical meaning
- Typical presentation
- Common causes
- Documentation context
(No citations, no sources.)
"""
    return perplexity_chat(system, user)

# ==========================================
# PDF BUILDER — STABLE VERSION
# ==========================================
def build_pdf(code, short_desc, long_desc, patient_text, clinical_text):
    if not isinstance(patient_text, str) or not patient_text.strip():
        patient_text = "No patient summary available."
    if not isinstance(clinical_text, str) or not clinical_text.strip():
        clinical_text = "No clinical summary available."

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    width, height = letter
    y = height - 60
    x = 50

    def wrap(text, size=10, lead=13):
        nonlocal y
        c.setFont("Helvetica", size)
        safe = text.replace("\t", " ")
        for line in textwrap.wrap(safe, width=90):
            if y < 60:
                c.showPage()
                y = height - 60
            c.drawString(x, y, line)
            y -= lead

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Hanvion Health – ICD-10 Summary")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, f"Code: {code}")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(x, y, f"Short: {short_desc}")
    y -= 16
    c.drawString(x, y, f"Long: {long_desc}")
    y -= 28

    # Patient section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Patient-friendly explanation")
    y -= 18
    wrap(patient_text)

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Clinical explanation")
    y -= 18
    wrap(clinical_text)

    y -= 30
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(x, y, "Generated for educational purposes only. © Hanvion Health")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

# ==========================================
# HEADER
# ==========================================
st.markdown("""
<div class="hanvion-header">
    <h1>Hanvion Health · ICD-10 Explorer</h1>
    <p>Search CMS-official ICD-10 codes. Generate patient & clinical summaries. PDF export included.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# SEARCH BAR + AUTOCOMPLETE
# ==========================================
search_col, sugg_col = st.columns([2, 1])

with search_col:
    query = st.text_input(
        "Search ICD-10 code or diagnosis",
        placeholder="Example: J45, asthma, diabetes, fracture..."
    )

suggestions = []
if query and len(query.strip()) >= 2:
    q = query.lower()
    mask = (
        df["code"].str.lower().str.startswith(q)
        | df["short_desc"].str.lower().str.contains(q)
    )
    suggestions = df[mask].head(8)

with sugg_col:
    if len(suggestions) > 0:
        label_list = ["(none)"] + [
            f"{row.code} — {row.short_desc}" for _, row in suggestions.iterrows()
        ]
        choice = st.selectbox("Suggestions", label_list)
        if choice != "(none)":
            query = choice.split(" — ")[0]

if not query.strip():
    st.info("Type at least 1–2 characters to search CMS ICD-10 codes.")
    st.stop()

# ==========================================
# FILTER RESULTS
# ==========================================
q = query.strip().lower()
mask_res = (
    df["code"].str.lower().str.contains(q)
    | df["short_desc"].str.lower().str.contains(q)
    | df["long_desc"].str.lower().str.contains(q)
)
filtered = df[mask_res]
total = len(filtered)

per_page = st.slider("Results per page", 5, 50, 15, 5)
max_page = max(1, (total - 1) // per_page + 1)
page = st.number_input("Page", min_value=1, max_value=max_page, value=1)

start = (page - 1) * per_page
end = start + per_page
page_df = filtered.iloc[start:end]

st.write(f"Showing {start + 1}–{min(end, total)} of {total} matches.")

# ==========================================
# RESULTS + AI + PDF
# ==========================================
for _, row in page_df.iterrows():
    code = row["code"]
    short_desc = row["short_desc"]
    long_desc = row["long_desc"]
    nf_excl = row["nf_excl"]

    with st.expander(f"{code} — {short_desc}", expanded=False):
        st.markdown(
            f"""
<div class="code-card">
    <div><b>{code}</b> — {short_desc}</div>
    <div style="font-size:14px; margin-top:4px;">{long_desc}</div>
    <div style="font-size:12px; opacity:0.7; margin-top:6px;">
        <b>NF EXCL:</b> {nf_excl if str(nf_excl).strip() else "None"}
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        clin_key = f"clin_{code}"
        pat_key = f"pat_{code}"

        colA, colB = st.columns(2)

        # --- Clinical summary ---
        with colA:
            st.subheader("Clinical explanation")
            if st.button("Generate clinical summary", key=f"btnclin_{code}"):
                with st.spinner("Querying AI…"):
                    text, err = get_clinical_summary(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.session_state[clin_key] = text

            if clin_key in st.session_state:
                st.write(st.session_state[clin_key])

        # --- Patient summary ---
        with colB:
            st.subheader("Patient explanation")
            if st.button("Generate patient summary", key=f"btnpat_{code}"):
                with st.spinner("Querying AI…"):
                    text, err = get_patient_summary(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.session_state[pat_key] = text

            if pat_key in st.session_state:
                st.write(st.session_state[pat_key])

        # --- PDF ---
        if clin_key in st.session_state and pat_key in st.session_state:
            patient_text = st.session_state.get(pat_key, "")
            clinical_text = st.session_state.get(clin_key, "")

            pdf_bytes = build_pdf(code, short_desc, long_desc, patient_text, clinical_text)

            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"{code}_ICD10_Hanvion.pdf",
                mime="application/pdf"
            )
        else:
            st.caption("Generate both summaries to download PDF.")
