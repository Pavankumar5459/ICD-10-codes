import streamlit as st
import pandas as pd
import requests

# ------------------------- PAGE CONFIG -------------------------
st.set_page_config(
    page_title="Hanvion Health – ICD-10 Explorer",
    page_icon="🩺",
    layout="wide"
)

# ------------------------- READ API KEY SAFELY -------------------------
PPLX_API_KEY = st.secrets["PPLX_API_KEY"]

# ------------------------- LOAD ICD DATA -------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df = df.rename(columns={
        "ICD_CODE": "code",
        "LONG_DESCRIPTION": "description"
    })
    return df

icd_df = load_icd10()

# ------------------------- AI CALL FUNCTION -------------------------
def perplexity_summary(prompt_text):
    """
    Calls Perplexity API safely from backend (no CORS issues).
    """

    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "pplx-70b",
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        # If not JSON → return raw text (helps with debugging)
        if "json" not in response.headers.get("Content-Type", ""):
            return f"API Error (HTML Response):\n\n{response.text}"

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"API Error: {e}"


# ------------------------- SIDEBAR SEARCH -------------------------
st.sidebar.header("Search ICD-10 Code")
query = st.sidebar.text_input("Enter ICD code or keyword")

search_results = icd_df[
    icd_df["code"].str.contains(query, case=False, na=False) |
    icd_df["description"].str.contains(query, case=False, na=False)
] if query else icd_df.head(20)

st.sidebar.write("### Results")
for _, row in search_results.iterrows():
    st.sidebar.write(f"**{row.code}** — {row.description}")


# ------------------------- MAIN PAGE -------------------------
st.title("🩺 Hanvion Health – ICD-10 Explorer")
st.write("Click any ICD-10 code to see details and AI explanations.")

# Accordion for each ICD code
for _, row in icd_df.iterrows():

    with st.expander(f"{row.code} — {row.description}"):

        st.markdown(f"### {row.code} — {row.description}")

        # AI Summary Columns
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Clinical explanation (educational only)")
            if st.button(f"Generate clinical summary for {row.code}", key=f"clinical_{row.code}"):
                with st.spinner("Generating clinical summary..."):
                    prompt = f"""
                    Provide a concise, medically accurate clinical explanation of ICD-10 code {row.code} ({row.description}).
                    Include:
                    - Pathophysiology
                    - Common symptoms
                    - Diagnostic considerations
                    - Typical treatment overview
                    Keep it formal and clinical.
                    """
                    summary = perplexity_summary(prompt)
                    st.write(summary)

        with col2:
            st.subheader("Patient explanation 🧑‍⚕️")
            if st.button(f"Generate patient summary for {row.code}", key=f"patient_{row.code}"):
                with st.spinner("Explaining in simple terms..."):
                    prompt = f"""
                    Explain ICD-10 code {row.code} ({row.description}) in SIMPLE patient-friendly language.
                    Include:
                    - What the condition is
                    - Why it happens
                    - Common symptoms
                    - When to see a doctor
                    - Reassurance and simple guidance
                    No medical jargon.
                    """
                    summary = perplexity_summary(prompt)
                    st.write(summary)
