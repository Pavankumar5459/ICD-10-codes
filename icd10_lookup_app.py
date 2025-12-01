import streamlit as st
import pandas as pd
import requests

# ======================================================
# Hanvion Health • ICD-10 Explorer (Premium)
# ======================================================

st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide"
)

# ======================================================
# Global UI Theme
# ======================================================
CUSTOM_CSS = """
<style>

html, body, [class*="st-"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
}

.hanvion-header {
    font-size: 40px;
    font-weight: 800;
}

.hanvion-sub {
    margin-top: -10px;
    font-size: 14px;
    color: #475569;
}

.code-card {
    background: #f7f5fc;
    border: 1px solid #e5e2f5;
    padding: 22px;
    border-radius: 12px;
    margin-bottom: 20px;
}

.muted {
    color: #667085;
}

.section-box {
    border: 1px solid #e5e7eb;
    padding: 18px;
    border-radius: 8px;
    background: #fafafa;
    margin-bottom: 10px;
}

</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ======================================================
# Load ICD-10 CMS Dataset
# ======================================================
@st.cache_data
def load_icd10():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    # Rename columns to standard names
    df = df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short_desc",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long_desc",
        "NF EXCL": "nf_excl"
    })

    return df


# ======================================================
# Perplexity API
# ======================================================
def perplexity_complete(prompt, api_key, model):
    """
    Generates AI text using Perplexity. No emojis, no HTML.
    """
    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"

        data = r.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI Error: {e}"


# ======================================================
# Sidebar (Filters + AI)
# ======================================================
with st.sidebar:
    st.markdown("### Hanvion Settings")
    st.markdown("Use this explorer to search valid CMS ICD-10 codes.")

    st.markdown("---")
    st.markdown("### AI (optional Perplexity)")

    perplexity_model = st.selectbox(
        "Perplexity model",
        options=[
            "pplx-7b-chat",
            "pplx-70b-chat",
            "pplx-7b-online",
            "pplx-70b-online"
        ],
        index=0
    )

    perplexity_key = st.text_input(
        "Perplexity API key",
        type="password",
        help="Paste your Perplexity key here"
    )

    st.markdown("---")
    st.markdown("Hanvion Health © 2025")

# ======================================================
# MAIN HEADER
# ======================================================
st.markdown('<div class="hanvion-header">Hanvion Health · ICD-10 Explorer</div>', unsafe_allow_html=True)
st.markdown('<div class="hanvion-sub">Search official ICD-10 codes using the CMS validated dataset. Explanations are educational only.</div>', unsafe_allow_html=True)

st.write("")

df = load_icd10()

# ======================================================
# SEARCH BOXES
# ======================================================
query = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: E11, diabetes, asthma, fracture"
)

results_per_page = st.number_input("Results per page", 5, 50, 20)
page = st.number_input("Page", 1, 5000, 1)

if query.strip() == "":
    st.info("Begin typing above to search ICD-10 codes.")
    st.stop()


# ======================================================
# SEARCH LOGIC
# ======================================================
mask = (
    df["code"].str.contains(query, case=False, na=False) |
    df["short_desc"].str.contains(query, case=False, na=False) |
    df["long_desc"].str.contains(query, case=False, na=False)
)

results = df[mask]

start = (page - 1) * results_per_page
end = start + results_per_page
display = results.iloc[start:end]

st.markdown(f"Showing **{len(results)}** matches.")

# ======================================================
# DISPLAY MATCHES
# ======================================================
for _, row in display.iterrows():

    st.markdown(f"""
    <div class="code-card">
        <h3>{row['code']} — {row['short_desc']}</h3>
        <p class="muted">{row['long_desc']}</p>
        <p class="muted"><b>NF EXCL:</b> {row['nf_excl']}</p>
    </div>
    """, unsafe_allow_html=True)

    # ============================
    # Clinical Explanation
    # ============================
    with st.expander("Clinical explanation (educational only)"):

        if st.button(f"Explain clinically: {row['code']}"):
            if perplexity_key.strip() == "":
                st.warning("Add your Perplexity API key in the sidebar.")
            else:
                prompt = f"""
                Provide a clinical explanation (medical-professional level, no HTML, no emojis)
                for ICD-10 code {row['code']}:

                Short description: {row['short_desc']}
                Long description: {row['long_desc']}

                Include:
                - Pathophysiology 
                - Common presentation
                - How clinicians differentiate this condition
                - Typical management considerations
                """
                ai_text = perplexity_complete(prompt, perplexity_key, perplexity_model)
                st.write(ai_text)

    # ============================
    # Patient Friendly Explanation
    # ============================
    with st.expander("Patient-friendly explanation"):

        if st.button(f"Explain simply: {row['code']}"):
            if perplexity_key.strip() == "":
                st.warning("Add your Perplexity API key.")
            else:
                prompt = f"""
                Explain the following ICD-10 condition in simple, easy-to-understand language.
                No emojis. No HTML.

                Code: {row['code']}
                Condition: {row['short_desc']}
                Description: {row['long_desc']}
                """
                ai_text = perplexity_complete(prompt, perplexity_key, perplexity_model)
                st.write(ai_text)

    # ============================
    # Compare Codes
    # ============================
    with st.expander("Compare with another ICD-10 code"):
        compare_code = st.text_input("Enter another ICD-10 code to compare", key=f"cmp_{row['code']}")

        if st.button(f"Compare {row['code']}"):
            if compare_code not in df["code"].values:
                st.error("Code not found in dataset.")
            else:
                other = df[df["code"] == compare_code].iloc[0]

                st.write("### Comparison")
                st.write(f"**{row['code']}** — {row['short_desc']}")
                st.write(f"**{other['code']}** — {other['short_desc']}")


# END OF FILE
