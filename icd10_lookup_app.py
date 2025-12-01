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
# Hanvion minimal UI styling (light, no emojis)
# ==========================================
st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Page background */
[data-testid="stAppViewContainer"] {
    background: #f7f9fc;
}

/* Header banner */
.hanvion-header {
    background: linear-gradient(90deg, #003f76, #006fc4);
    padding: 40px 32px;
    border-radius: 16px;
    color: white;
    text-align: center;
    margin-bottom: 32px;
}
.hanvion-header h1 {
    margin-bottom: 8px;
    font-size: 32px;
    font-weight: 700;
}
.hanvion-header p {
    margin: 0;
    font-size: 15px;
    opacity: 0.9;
}

/* Result card inside expander */
.code-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 20px;
    margin-top: 10px;
}
.code-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 6px;
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

/* Tighten expanders a bit */
.streamlit-expanderHeader {
    font-size: 15px;
    font-weight: 600;
}
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# Load ICD-10 dataset
# ==========================================
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str,
    ).fillna("")

    df = df.rename(
        columns={
            "CODE": "code",
            "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_desc",
            "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_desc",
            "NF EXCL": "nf_excl",
        }
    )

    # Keep only what we use
    return df[["code", "short_desc", "long_desc", "nf_excl"]]


df = load_icd10()

# ==========================================
# Perplexity AI helper
# ==========================================
def call_perplexity(messages, system_prompt=None):
    """
    Call Perplexity chat completions API with sonar-pro.

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
        "model": "sonar-pro",
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

        # If status is not 200, show plain text so user sees the real error
        if resp.status_code != 200:
            return None, f"AI HTTP {resp.status_code}: {resp.text[:400]}"

        # Parse JSON safely
        data = resp.json()
        if "choices" not in data or not data["choices"]:
            return None, f"AI Error: unexpected response structure: {data}"

        return data["choices"][0]["message"]["content"], None

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
# Search controls
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
# Filter results
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
# Results list: click row → expanded card with description + AI
# ==========================================
for _, row in page_df.iterrows():
    code = row["code"]
    short_desc = row["short_desc"]
    long_desc = row["long_desc"]
    nf_excl = row["nf_excl"]

    # Expander acts like your "pop up when clicked"
    with st.expander(f"{code} — {short_desc}", expanded=False):
        # Core disease description
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

        # Two columns: clinical explanation / patient explanation
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Clinical explanation (educational only)")
            if st.button(f"Generate clinical summary for {code}", key=f"clin_{code}"):
                with st.spinner("Contacting AI for clinical explanation…"):
                    text, err = get_clinical_explanation(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.write(text)

        with c2:
            st.subheader("Patient explanation")
            if st.button(f"Generate patient summary for {code}", key=f"pat_{code}"):
                with st.spinner("Contacting AI for patient explanation…"):
                    text, err = get_patient_explanation(code, short_desc, long_desc)
                if err:
                    st.error(err)
                else:
                    st.write(text)
