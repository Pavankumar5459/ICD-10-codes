import streamlit as st
import pandas as pd
import requests

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="Hanvion Health – ICD-10 Explorer",
    page_icon="🩺",
    layout="wide"
)

# ------------------- READ API KEY -------------------
PPLX_API_KEY = st.secrets["PPLX_API_KEY"]

# ------------------- LOAD ICD-10 DATA -------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")

    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()

    # Your real column names from screenshot
    code_col = "code"
    desc_col = "long description (valid icd-10 fy2025)"

    # Ensure both exist
    if code_col not in df.columns:
        st.error(f"❌ Could not find ICD-10 code column '{code_col}' in Excel file.")
        st.write("Available columns:", df.columns.tolist())
        st.stop()

    if desc_col not in df.columns:
        st.error(f"❌ Could not find description column '{desc_col}' in Excel file.")
        st.write("Available columns:", df.columns.tolist())
        st.stop()

    # Rename for consistent access
    df = df.rename(columns={
        code_col: "code",
        desc_col: "description"
    })

    # Keep only needed columns
    return df[["code", "description"]]

icd_df = load_icd10()

# ------------------- PERPLEXITY API CALL FUNCTION -------------------
def perplexity_summary(prompt_text):
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

        # Handle HTML error (401/403 Cloudflare)
        if "json" not in response.headers.get("Content-Type", ""):
            return f"API Error (HTML Response):\n\n{response.text}"

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"API Error: {e}"

# ------------------- SIDEBAR SEARCH -------------------
st.sidebar.header("Search ICD-10 Code")
query = st.sidebar.text_input("Enter ICD code or keyword")

search_results = icd_df[
    icd_df["code"].str.contains(query, case=False, na=False) |
    icd_df["description"].str.contains(query, case=False, na=False)
] if query else icd_df.head(20)

st.sidebar.write("### Results")
for _, row in search_results.iterrows():
    st.sidebar.write(f"**{row['code']}** — {row['description']}")

# ------------------- MAIN PAGE -------------------
st.title("🩺 Hanvion Health – ICD-10 Explorer")
st.write("Browse ICD-10 codes and generate AI explanations.")

# ------------------- ICD DISPLAY + BUTTONS -------------------
for _, row in icd_df.iterrows():

    with st.expander(f"{row['code']} — {row['description']}"):

        st.markdown(f"### {row['code']} — {row['description']}")

        col1, col2 = st.columns(2)

        # ----------- Clinical Summary -----------
        with col1:
            st.subheader("Clinical explanation (for educational use)")
            if st.button(f"Clinical summary for {row['code']}", key=f"clinical_{row['code']}"):
                with st.spinner("Generating clinical summary..."):
                    prompt = f"""
                    Provide a concise, medically accurate clinical explanation of ICD-10 code {row['code']} ({row['description']}).
                    Include:
                    - Clinical definition
                    - Symptoms
                    - Diagnostic approach
                    - Typical treatment
                    Write professionally and clinically.
                    """
                    st.write(perplexity_summary(prompt))

        # ----------- Patient Summary -----------
        with col2:
            st.subheader("Patient explanation 🧑‍⚕️")
            if st.button(f"Patient summary for {row['code']}", key=f"patient_{row['code']}"):
                with st.spinner("Explaining in simple terms..."):
                    prompt = f"""
                    Explain ICD-10 code {row['code']} ({row['description']}) in simple patient-friendly language.
                    Include:
                    - What the condition is
                    - Why it happens
                    - Common symptoms
                    - When to see a doctor
                    Avoid medical jargon. Keep it supportive and clear.
                    """
                    st.write(perplexity_summary(prompt))
