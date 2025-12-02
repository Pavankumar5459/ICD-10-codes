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
# GLOBAL CSS (LIGHT + DARK)
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
    color: #ffffff;
    padding: 24px 28px;
    border-radius: 18px;
    box-shadow: 0 14px 28px rgba(15,23,42,0.38);
    margin-bottom: 18px;
}
.hanvion-header h1 { margin: 0 0 4px; font-size: 26px; font-weight: 700; }
.hanvion-header p { margin: 0; font-size: 14px; opacity: 0.95; }

.code-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px 18px;
    margin-top: 4px;
}
.code-title { font-size: 17px; font-weight: 600; margin-bottom: 4px; }
.code-long { font-size: 14px; color: #1f2933; }
.code-extra { font-size: 12px; color: #4b5563; margin-top: 4px; }

.small-muted { font-size: 12px; color: #6b7280; }

div[data-baseweb="input"] > input {
    font-size: 15px;
    padding-top: 10px;
    padding-bottom: 10px;
}
</style>
"""

DARK_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
[data-testid="stAppViewContainer"] {
    background: #020617;
    color: #e5e7eb;
}
.hanvion-header {
    background: radial-gradient(circle at top left, #38bdf8, #0f172a);
    color: #e5e7eb;
    padding: 24px 28px;
    border-radius: 18px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.7);
    margin-bottom: 18px;
}
.hanvion-header h1 { margin: 0 0 4px; font-size: 26px; font-weight: 700; }
.hanvion-header p { margin: 0; font-size: 14px; opacity: 0.9; }

.code-card {
    background: #020617;
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 16px 18px;
    margin-top: 4px;
}
.code-title { font-size: 17px; font-weight: 600; margin-bottom: 4px; color: #e5e7eb; }
.code-long { font-size: 14px; color: #d1d5db; }
.code-extra { font-size: 12px; color: #9ca3af; margin-top: 4px; }

.small-muted { font-size: 12px; color: #9ca3af; }

div[data-baseweb="input"] > input {
    font-size: 15px;
    padding-top: 10px;
    padding-bottom: 10px;
    color: #e5e7eb;
}
</style>
"""

st.markdown(DARK_CSS if dark_mode else LIGHT_CSS, unsafe_allow_html=True)

# ==========================================
# LOAD ICD-10 DATA
# ==========================================
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.lower().str.strip()

    df = df.rename(
        columns={
            "code": "code",
            "short description (valid icd-10 fy2025)": "short_desc",
            "long description (valid icd-10 fy2025)": "long_desc",
        }
    )

    if "nf excl" in df.columns:
        df["nf_excl"] = df["nf excl"]
    else:
        df["nf_excl"] = ""

    return df[["code", "short_desc", "long_desc", "nf_excl"]].sort_values("code")


df = load_icd10()

# ==========================================
# PERPLEXITY CHAT HELPER (SONAR-PRO)
# ==========================================
def perplexity_chat(system_prompt: str, user_prompt: str):
    api_key = st.secrets.get("PPLX_API_KEY")
    if not api_key:
        return None, "Perplexity API key (PPLX_API_KEY) is missing in Streamlit secrets."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-pro",  # modern, valid Perplexity model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 600,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            return None, f"AI HTTP {resp.status_code}: {resp.text[:400]}"

        data = resp.json()

        # Newer formats
        if "output_text" in data:
            return data["output_text"], None
        if "response" in data:
            return data["response"], None

        # OpenAI-style fallback
        if "choices" in data and data["choices"]:
            msg = data["choices"][0].get("message", {})
            content = msg.get("content")
            if content:
                return content, None

        return None, f"AI Error: unexpected response structure: {data}"
    except Exception as e:
        return None, f"AI Error: {e}"


@st.cache_data(show_spinner=False)
def get_clinical_summary(code: str, short_desc: str, long_desc: str):
    system = (
        "You are an ICD-10 educator for clinicians. "
        "You explain codes clearly for medical professionals and coders. "
        "Do NOT provide treatment recommendations or medical advice."
    )
    user = f"""
Provide a concise clinical explanation for ICD-10 code {code}.

Short description: {short_desc}
Long description: {long_desc}

Include:
- Clinical meaning and typical presentation
- Common causes or risk factors
- Typical documentation context (e.g., inpatient vs outpatient)
Avoid advice or specific treatments.
"""
    return perplexity_chat(system, user)


@st.cache_data(show_spinner=False)
def get_patient_summary(code: str, short_desc: str, long_desc: str):
    system = (
        "You explain medical information in very simple language for patients. "
        "You are calm, clear, and avoid jargon. "
        "You never give medical advice or specific treatments."
    )
    user = f"""
Explain ICD-10 code {code} so a non-medical person can understand.

Short description: {short_desc}
Long description: {long_desc}

Explain:
- What the condition means in everyday words
- Common symptoms / what people might notice
- High level of when it's important to speak to a doctor (no urgent/emergency advice)
Do NOT give treatment or medication suggestions.
"""
    return perplexity_chat(system, user)

# ==========================================
# PDF GENERATION (SAFE)
# ==========================================
def build_pdf(code: str, short_desc: str, long_desc: str,
              patient_text: str, clinical_text: str) -> bytes:
    # Ensure both texts are strings
    if not isinstance(patient_text, str) or not patient_text.strip():
        patient_text = "No patient-friendly summary was generated."
    if not isinstance(clinical_text, str) or not clinical_text.strip():
        clinical_text = "No clinical summary was generated."

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    x_margin = 50
    y = height - 60

    def draw_wrapped(text, font_size=10, leading=13):
        nonlocal y
        c.setFont("Helvetica", font_size)
        safe_text = text.replace("\t", " ")
        for line in textwrap.wrap(safe_text, width=90):
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", font_size)
            c.drawString(x_margin, y, line)
            y -= leading

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, "Hanvion Health – ICD-10 Explanation")
    y -= 24

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, f"Code: {code}")
    y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(x_margin, y, f"Short description: {short_desc}")
    y -= 14
    c.drawString(x_margin, y, f"Long description: {long_desc}")
    y -= 24

    # Patient section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, "Patient-friendly explanation")
    y -= 16
    draw_wrapped(patient_text)

    y -= 18

    # Clinical section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, "Clinical explanation (educational only)")
    y -= 16
    draw_wrapped(clinical_text)

    y -= 24
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        x_margin,
        y,
        "Generated for educational purposes only. Not medical advice. © Hanvion Health",
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

# ==========================================
# HEADER BLOCK
# ==========================================
st.markdown(
    """
<div class="hanvion-header">
  <h1>Hanvion Health · ICD-10 Explorer</h1>
  <p>Search official CMS ICD-10 codes and generate patient + clinical explanations (for education only).</p>
</div>
""",
    unsafe_allow_html=True,
)

if not st.secrets.get("PPLX_API_KEY"):
    st.warning("AI explanations are disabled until PPLX_API_KEY is set in Streamlit secrets.", icon="⚠️")

# ==========================================
# SEARCH + AUTOCOMPLETE
# ==========================================
search_col, suggest_col = st.columns([2, 1])

with search_col:
    query = st.text_input(
        "Search ICD-10 code or diagnosis",
        placeholder="Example: J45, asthma, fracture, diabetes…",
    )

suggest_options = []
if query and len(query.strip()) >= 2:
    q = query.strip().lower()
    mask_suggest = (
        df["code"].str.lower().str.startswith(q)
        | df["short_desc"].str.lower().str.contains(q)
    )
    suggestions_df = df[mask_suggest].head(8)
    suggest_options = [
        f"{row.code} — {row.short_desc}" for _, row in suggestions_df.iterrows()
    ]

with suggest_col:
    if suggest_options:
        picked = st.selectbox("Suggestions", ["(none)"] + suggest_options)
        if picked != "(none)":
            # If user picks a suggestion, set query to the code part
            query = picked.split(" — ")[0]

st.markdown(
    f"<p class='small-muted'>Showing codes that match: <strong>{query or '(no query)'}</strong></p>",
    unsafe_allow_html=True,
)

if not query or not query.strip():
    st.info("Type a code or diagnosis above to see matching ICD-10 codes.")
    st.stop()

# ==========================================
# FILTER RESULTS
# ==========================================
q = query.strip().lower()
mask = (
    df["code"].str.lower().str.contains(q)
    | df["short_desc"].str.lower().str.contains(q)
    | df["long_desc"].str.lower().str.contains(q)
)
filtered = df[mask]
total = len(filtered)

per_page = st.slider("Results per page", 5, 50, 15, 5)
max_page = max(1, (total - 1) // per_page + 1)
page = st.number_input("Page", min_value=1, max_value=max_page, value=1)

start = (page - 1) * per_page
end = start + per_page
page_df = filtered.iloc[start:end]

st.write(f"Showing {start + 1}–{min(end, total)} of {total} matching result(s).")

# ==========================================
# RESULTS + AI + PDF
# ==========================================
for _, row in page_df.iterrows():
    code = row["code"]
    short_desc = row["short_desc"]
    long_desc = row["long_desc"]
    nf_excl = row["nf_excl"]

    with st.expander(f"{code} — {short_desc}", expanded=False):
        # Code details
        st.markdown(
            f"""
<div class="code-card">
  <div class="code-title">{code} — {short_desc}</div>
  <div class="code-long">{long_desc}</div>
  <div class="code-extra"><strong>NF EXCL:</strong> {nf_excl if str(nf_excl).strip() else "None listed."}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("")

        colA, colB = st.columns(2)

        clin_key = f"clin_{code}"
        pat_key = f"pat_{code}"

        # --- Clinical explanation ---
        with colA:
            st.subheader("Clinical explanation (educational)")
            if st.button("Generate clinical summary", key=f"btn_clin_{code}"):
                with st.spinner("Generating clinical explanation…"):
                    text, err = get_clinical_summary(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.session_state[clin_key] = text

            if clin_key in st.session_state:
                st.write(st.session_state[clin_key])

        # --- Patient explanation ---
        with colB:
            st.subheader("Patient explanation")
            if st.button("Generate patient summary", key=f"btn_pat_{code}"):
                with st.spinner("Generating patient explanation…"):
                    text, err = get_patient_summary(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.session_state[pat_key] = text

            if pat_key in st.session_state:
                st.write(st.session_state[pat_key])

        # --- PDF download (if both are available) ---
        if clin_key in st.session_state and pat_key in st.session_state:
            patient_text = st.session_state.get(pat_key, "")
            clinical_text = st.session_state.get(clin_key, "")

            pdf_bytes = build_pdf(
                code,
                short_desc,
                long_desc,
                patient_text,
                clinical_text,
            )

            st.download_button(
                label="📄 Download PDF (patient + clinical)",
                data=pdf_bytes,
                file_name=f"{code}_hanvion_icd10_summary.pdf",
                mime="application/pdf",
            )
        else:
            st.caption("Generate both explanations to enable PDF download.")
