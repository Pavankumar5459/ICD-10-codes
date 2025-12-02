import streamlit as st
import pandas as pd
import requests

# ==========================================
# Page config
# ==========================================
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
)

# ==========================================
# Hanvion UI styling
# ==========================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* App background */
[data-testid="stAppViewContainer"] {
    background: #f7f9fc;
}

/* Header banner */
.hanvion-header {
    background: linear-gradient(90deg, #004c97, #0077b6);
    color: #ffffff;
    padding: 24px 28px;
    border-radius: 18px;
    box-shadow: 0 14px 28px rgba(15,23,42,0.35);
    margin-bottom: 18px;
}
.hanvion-header h1 {
    margin: 0 0 4px 0;
    font-size: 26px;
    font-weight: 700;
}
.hanvion-header p {
    margin: 0;
    font-size: 14px;
    opacity: 0.93;
}

/* Result card inside expander */
.code-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 20px;
    margin-top: 6px;
}
.code-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
}
.code-long {
    font-size: 14px;
    color: #1f2933;
}
.code-extra {
    font-size: 13px;
    color: #4b5563;
    margin-top: 6px;
}

/* Small help text */
.small-muted {
    font-size: 12px;
    color: #6b7280;
}

/* Make text input look like a big search bar */
div[data-baseweb="input"] > input {
    font-size: 15px;
    padding-top: 10px;
    padding-bottom: 10px;
}
</style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# Load ICD-10 data
# ==========================================
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.lower().str.strip()

    # Map your actual CMS columns
    df = df.rename(
        columns={
            "code": "code",
            "short description (valid icd-10 fy2025)": "short_desc",
            "long description (valid icd-10 fy2025)": "long_desc",
        }
    )

    # Optional NF EXCL flag -> Included / Excluded
    if "nf excl" in df.columns:
        df["nf_excl"] = df["nf excl"]
    else:
        df["nf_excl"] = ""

    df = df[["code", "short_desc", "long_desc", "nf_excl"]]
    return df.sort_values("code").reset_index(drop=True)


df = load_icd10()

# ==========================================
# Perplexity AI helper (universal handler)
# ==========================================
def call_perplexity(messages, system_prompt=None):
    """
    Call Perplexity chat completions API (supports old & new response formats).

    Returns (text, error_message)
    """
    api_key = st.secrets.get("PPLX_API_KEY")
    if not api_key:
        return None, "Perplexity API key (PPLX_API_KEY) is not set in Streamlit secrets."

    url = "https://api.perplexity.ai/chat/completions"

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    payload = {
        "model": "pplx-70b",  # or sonar-pro if you prefer
        "messages": full_messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)

        if resp.status_code != 200:
            return None, f"AI HTTP {resp.status_code}: {resp.text[:400]}"

        data = resp.json()

        # New Perplexity-style
        if isinstance(data, dict):
            if "output_text" in data:
                return data["output_text"], None
            if "response" in data:
                return data["response"], None

            # OpenAI-style choices
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                content = msg.get("content")
                if content:
                    return content, None

        return None, f"AI Error: unexpected response structure: {data}"

    except Exception as e:
        return None, f"AI Error: {e}"


def get_clinical_explanation(code, short_desc, long_desc):
    system_prompt = (
        "You are a clinical ICD-10 educator. You explain codes clearly for clinicians. "
        "Do not give treatment recommendations; keep it educational only."
    )
    user_prompt = f"""
Provide a concise but informative clinical explanation for ICD-10 code {code}.

Short description: {short_desc}
Long description: {long_desc}

Include:
- Clinical meaning and typical presentation
- Common causes or risk factors
- Typical settings where this code is used (inpatient vs outpatient)
- Any important distinctions from nearby or similar ICD-10 codes

Do not give medical advice or treatment recommendations. Educational only.
"""
    return call_perplexity(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
    )


def get_patient_explanation(code, short_desc, long_desc):
    system_prompt = (
        "You explain medical information in simple language for patients. "
        "You are calm, clear, and avoid technical jargon. You do not give medical advice."
    )
    user_prompt = f"""
Explain ICD-10 code {code} in simple language that a non-medical person can understand.

Short description: {short_desc}
Long description: {long_desc}

Explain:
- What this condition means in everyday terms
- Common symptoms or what someone might notice
- When it is usually important to talk to a doctor

Do not give medical advice, do not recommend specific treatments.
Just explain the condition in plain language.
"""
    return call_perplexity(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
    )

# ==========================================
# Header
# ==========================================
st.markdown(
    """
<div class="hanvion-header">
  <h1>Hanvion Health · ICD-10 Explorer</h1>
  <p>Search official CMS ICD-10 codes and view structured descriptions with optional AI explanations.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ==========================================
# Search controls (SINGLE search bar)
# ==========================================
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    query = st.text_input(
        "Search ICD-10 code or diagnosis",
        placeholder="Example: J45, asthma, fracture, diabetes…",
    )

with col2:
    per_page = st.number_input("Results per page", 5, 50, 20)

with col3:
    page = st.number_input("Page", 1, 10_000, 1)

if not query.strip():
    st.info("Start typing above to search ICD-10 codes.")
    st.stop()

# ==========================================
# Filter + paginate results
# ==========================================
q = query.strip().lower()
mask = (
    df["code"].str.lower().str.contains(q)
    | df["short_desc"].str.lower().str.contains(q)
    | df["long_desc"].str.lower().str.contains(q)
)
filtered = df[mask]

total = len(filtered)
start = (page - 1) * per_page
end = start + per_page
page_df = filtered.iloc[start:end]

st.write(f"Showing {start + 1}–{min(end, total)} of {total} result(s).")

# ==========================================
# Results list
# ==========================================
for _, row in page_df.iterrows():
    code = row["code"]
    short_desc = row["short_desc"]
    long_desc = row["long_desc"]
    nf_excl = row["nf_excl"]

    with st.expander(f"{code} — {short_desc}", expanded=False):
        # Code details card
        st.markdown(
            f"""
<div class="code-card">
  <div class="code-title">{code} — {short_desc}</div>
  <div class="code-long">{long_desc}</div>
  <div class="code-extra"><strong>NF EXCL:</strong> {nf_excl if nf_excl else "None listed."}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        c1, c2 = st.columns(2)

        # Clinical explanation
        with c1:
            st.subheader("Clinical explanation (educational only)")
            if st.button(f"Generate clinical summary for {code}", key=f"clin_{code}"):
                with st.spinner("Contacting AI for clinical explanation…"):
                    text, err = get_clinical_explanation(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.write(text)

        # Patient explanation
        with c2:
            st.subheader("Patient explanation")
            if st.button(f"Generate patient summary for {code}", key=f"pat_{code}"):
                with st.spinner("Contacting AI for patient explanation…"):
                    text, err = get_patient_explanation(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.write(text)
