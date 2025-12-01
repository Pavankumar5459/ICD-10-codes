import streamlit as st
import pandas as pd
import requests
import base64

# ------------------------------------------------------------
#  PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Hanvion Health · ICD-10 Explorer",
    layout="wide",
    page_icon="💠",
)

# ------------------------------------------------------------
#  HANVION PREMIUM UI (Light + Dark)
# ------------------------------------------------------------
st.markdown("""
<style>

html, body, .stApp {
    font-family: 'Inter', sans-serif;
}

/* HEADER CARD */
.hanvion-header {
    background: linear-gradient(90deg, #003a70, #005a9c);
    padding: 32px 40px;
    border-radius: 16px;
    color: white;
    margin-bottom: 32px;
}

/* CARD */
.hcard {
    background: var(--card-bg);
    padding: 22px;
    border-radius: 14px;
    border: 1px solid var(--card-border);
    margin-bottom: 20px;
}

/* DARK MODE */
@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: #1e293b;
        --card-border: #334155;
        --text-muted: #cbd5e1;
    }
    body, .stApp {
        background: #0f172a;
        color: white;
    }
}

/* LIGHT MODE */
@media (prefers-color-scheme: light) {
    :root {
        --card-bg: white;
        --card-border: #e5e7eb;
        --text-muted: #475569;
    }
    body, .stApp {
        background: #f8fafc;
        color: #1e293b;
    }
}

.muted { color: var(--text-muted); font-size:14px; }

</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
#  LOAD ICD-10 DATA
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str
    ).fillna("")

    df.rename(columns={
        "CODE": "code",
        "SHORT DESCRIPTION (VALID ICD-10 FY2025)": "short",
        "LONG DESCRIPTION (VALID ICD-10 FY2025)": "long",
        "NF EXCL": "nf_excl"
    }, inplace=True)

    return df


df = load_data()


# ------------------------------------------------------------
#  PERPLEXITY AI (secret key only)
# ------------------------------------------------------------
def ask_perplexity(prompt):
    try:
        api_key = st.secrets["perplexity"]["API_KEY"]
    except:
        return "❗ Perplexity AI key is not configured in Streamlit Secrets."

    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "pplx-7b-chat",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        if r.status_code != 200:
            return f"AI Error {r.status_code}: {r.text}"

        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"AI Error: {str(e)}"


# ------------------------------------------------------------
#  HEADER SECTION
# ------------------------------------------------------------
st.markdown("""
<div class="hanvion-header">
    <h1 style="margin:0;">Hanvion Health · ICD-10 Explorer</h1>
    <p style="margin-top:6px; opacity:0.9;">Search official CMS ICD-10 codes with AI-powered educational summaries.</p>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
#  SEARCH CONTROLS
# ------------------------------------------------------------
query = st.text_input(
    "Search ICD-10 code or diagnosis",
    placeholder="Example: J45, asthma, fracture, diabetes…"
)

colA, colB = st.columns(2)
with colA:
    per_page = st.number_input("Results per page", 5, 50, 20)
with colB:
    page = st.number_input("Page", 1, 5000, 1)


# ------------------------------------------------------------
#  SEARCH LOGIC
# ------------------------------------------------------------
if query.strip() == "":
    st.info("Begin typing above to search ICD-10 codes.")
    st.stop()

mask = (
    df["code"].str.contains(query, case=False, na=False)
    | df["short"].str.contains(query, case=False, na=False)
    | df["long"].str.contains(query, case=False, na=False)
)

results = df[mask]
total = len(results)

start = (page - 1) * per_page
end = start + per_page

subset = results.iloc[start:end]

st.write(f"Showing {start+1:,}–{min(end, total):,} of {total:,} results.")


# ------------------------------------------------------------
#  DISPLAY RESULTS
# ------------------------------------------------------------
for _, row in subset.iterrows():

    st.markdown(f"""
    <div class="hcard">
        <h3>{row['code']} — {row['short']}</h3>
        <p class="muted">{row['long']}</p>
    """, unsafe_allow_html=True)

    # --- Clinical explanation ---
    with st.expander("Clinical explanation (educational only)"):
        if st.button(f"Explain clinically: {row['code']}", key=f"clin_{row['code']}"):
            text = ask_perplexity(
                f"Provide a clinical explanation for ICD-10 code {row['code']}: {row['long']}."
            )
            st.write(text)

    # --- Patient summary ---
    with st.expander("Patient-friendly explanation"):
        if st.button(f"Explain simply: {row['code']}", key=f"pat_{row['code']}"):
            text = ask_perplexity(
                f"Explain ICD-10 code {row['code']} ({row['long']}) in simple patient-friendly language."
            )
            st.write(text)

    # --- NF EXCL ---
    with st.expander("NF Exclusion details"):
        st.write(row["nf_excl"] if row["nf_excl"] else "Not specified.")

    st.markdown("</div>", unsafe_allow_html=True)
