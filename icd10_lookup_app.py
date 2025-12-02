import streamlit as st
import pandas as pd
import requests

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="ICD-10 Lookup Dashboard – Hanvion Health",
    page_icon="🩺",
    layout="wide",
)

# -------------------------------------------------
# GLOBAL CSS (UI + Voice button styling)
# -------------------------------------------------
st.markdown("""
<style>
.stApp {
    background-color: #f4f7fb;
    font-family: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI", sans-serif;
}

/* Remove top padding */
.block-container { padding-top: 1.5rem; }

/* Hero card */
.hero-card {
    background: linear-gradient(135deg, #004c97, #0077b6);
    border-radius: 1.5rem;
    padding: 2.5rem 3rem;
    color: white;
    box-shadow: 0 18px 35px rgba(0,0,0,0.22);
    margin-bottom: 1.75rem;
}
.hero-title {
    font-size: 2.2rem; font-weight: 700;
}
.hero-subtitle {
    font-size: 1rem; opacity: 0.95; max-width: 640px;
}
.hero-badge {
    margin-top: 0.7rem; padding: 0.3rem 0.8rem;
    background: rgba(255,255,255,0.26);
    border-radius: 20px; display: inline-block;
    font-size: 0.8rem;
}

/* Search bar container in header */
.search-container {
    margin-top: 1.4rem;
    background: rgba(255,255,255,0.18);
    padding: 12px;
    border-radius: 12px;
    backdrop-filter: blur(6px);
    display: flex;
    gap: 10px;
    align-items: center;
}

/* Search input */
#icd_search_input {
    flex: 1;
    padding: 10px 14px;
    border-radius: 8px;
    border: none;
    outline: none;
    font-size: 15px;
}

/* Icon search button */
.search-btn {
    background: white;
    border: none;
    font-size: 20px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.18);
}

/* Mic button */
.mic-btn {
    background: #ff4757;
    color: white;
    border: none;
    font-size: 18px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.18);
}
.mic-btn.listening {
    background: #2ed573 !important;
}

/* Soft card */
.soft-card {
    background: white;
    padding: 1.3rem 1.4rem;
    border-radius: 1rem;
    box-shadow: 0 10px 25px rgba(0,0,0,0.07);
    margin-bottom: 1rem;
}

/* AI box */
.ai-box {
    background: #f8fafc;
    padding: 1rem;
    border-radius: 0.8rem;
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# READ API KEY
# -------------------------------------------------
try:
    PPLX_API_KEY = st.secrets["PPLX_API_KEY"]
except:
    PPLX_API_KEY = None

# -------------------------------------------------
# PERPLEXITY API — UNIVERSAL HANDLER
# -------------------------------------------------
def call_perplexity(prompt):
    if not PPLX_API_KEY:
        return "⚠️ AI not configured: Add PPLX_API_KEY in Streamlit Secrets."

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "pplx-70b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=40)

        if "json" not in resp.headers.get("Content-Type", ""):
            return f"⚠️ Unexpected response:\n\n{resp.text[:800]}"

        data = resp.json()

        if "output_text" in data:
            return data["output_text"]

        if "response" in data:
            return data["response"]

        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]

        return f"⚠️ Unknown response:\n\n{data}"

    except Exception as e:
        return f"API Error: {e}"

# -------------------------------------------------
# AI SUMMARIES (Patient + Clinical)
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def get_ai_summary(code, desc, mode):
    if mode == "patient":
        prompt = f"""
        Explain ICD-10 code {code} ({desc}) in simple patient-friendly language.
        Include symptoms, meaning, when to see a doctor.
        Keep under 200 words.
        """
    else:
        prompt = f"""
        Provide a clinical summary for ICD-10 code {code} ({desc}).
        Include definition, symptoms, diagnostics, and management.
        """

    return call_perplexity(prompt)

# -------------------------------------------------
# LOAD ICD-10 DATA
# -------------------------------------------------
@st.cache_data
def load_icd10():
    df = pd.read_excel("section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx")
    df.columns = df.columns.str.lower().str.strip()

    df = df.rename(columns={
        "code": "code",
        "short description (valid icd-10 fy2025)": "short_desc",
        "long description (valid icd-10 fy2025)": "long_desc",
    })

    if "nf excl" in df.columns:
        df["code_type"] = df["nf excl"].apply(lambda x: "Excluded" if str(x).strip() else "Included")
    else:
        df["code_type"] = "Included"

    return df[["code", "short_desc", "long_desc", "code_type"]].sort_values("code")

icd_df = load_icd10()

# -------------------------------------------------
# HERO HEADER WITH SEARCH + MIC
# -------------------------------------------------
st.markdown("""
<div class="hero-card">
  <div class="hero-title">ICD-10 Lookup Dashboard</div>
  <div class="hero-subtitle">Search ICD-10 with AI + Voice.</div>
  <div class="hero-badge">Hanvion Health • CMS 2026 ICD-10 Update</div>

  <div class="search-container">
    <input id="icd_search_input" type="text" placeholder="Search ICD-10 Code or Diagnosis…" />
    <button class="mic-btn" id="voiceBtn">🎤</button>
    <button class="search-btn" id="searchBtn">🔍</button>
  </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# JS FOR VOICE SEARCH + ENTER/ESC
# -------------------------------------------------
st.markdown("""
<script>
let recognizing = false;

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("icd_search_input");
    const searchBtn = document.getElementById("searchBtn");
    const voiceBtn = document.getElementById("voiceBtn");

    // ENTER triggers search
    input.addEventListener("keypress", function(e) {
        if (e.key === "Enter") { searchBtn.click(); }
    });

    // ESC clears
    input.addEventListener("keydown", function(e) {
        if (e.key === "Escape") { input.value = ""; }
    });

    // Voice recognition
    if (!('webkitSpeechRecognition' in window)) {
        console.log("Speech Recognition not supported.");
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    voiceBtn.addEventListener("click", () => {
        if (!recognizing) {
            recognizing = true;
            voiceBtn.classList.add("listening");
            recognition.start();
        } else {
            recognizing = false;
            voiceBtn.classList.remove("listening");
            recognition.stop();
        }
    });

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        input.value = text;
        recognizing = false;
        voiceBtn.classList.remove("listening");
        searchBtn.click();
    };

    recognition.onerror = () => {
        recognizing = false;
        voiceBtn.classList.remove("listening");
    };
});
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------
# STREAMLIT HIDDEN SEARCH CAPTURE
# -------------------------------------------------
query = st.text_input("hidden_query", key="query_holder", label_visibility="collapsed")

if st.button("Trigger_Search", key="trigger_hidden"):
    pass

# Sync JS value into Streamlit
query = st.session_state.get("search_box", "")

# -------------------------------------------------
# SEARCH LOGIC
# -------------------------------------------------
if query:
    df_filtered = icd_df[
        icd_df["code"].str.contains(query, case=False, na=False)
        | icd_df["short_desc"].str.contains(query, case=False, na=False)
        | icd_df["long_desc"].str.contains(query, case=False, na=False)
    ]
else:
    df_filtered = icd_df.head(40)

# -------------------------------------------------
# RESULTS + AI PANEL
# -------------------------------------------------
c1, c2 = st.columns([2.2, 1.8])

with c1:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.write("### ICD-10 Results")

    st.dataframe(
        df_filtered.rename(columns={
            "code": "ICD-10 Code",
            "short_desc": "Short Description",
            "long_desc": "Long Description",
            "code_type": "Type"
        }),
        hide_index=True,
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)

    st.write("### AI Explanations (Patient + Clinical)")

    if df_filtered.empty:
        st.write("Search something first.")
    else:
        select = st.selectbox(
            "Choose code:",
            df_filtered.index,
            format_func=lambda i: f"{df_filtered.loc[i,'code']} — {df_filtered.loc[i,'short_desc']}"
        )

        row = df_filtered.loc[select]

        st.write(f"**{row['code']} — {row['long_desc']}**")

        auto = st.checkbox("Auto-generate", value=True)

        btn = st.button("Generate / Refresh")

        p_text = ""
        c_text = ""

        if auto or btn:
            with st.spinner("Generating AI summaries..."):
                p_text = get_ai_summary(row["code"], row["long_desc"], "patient")
                c_text = get_ai_summary(row["code"], row["long_desc"], "clinical")

        if p_text:
            st.markdown('<div class="ai-box"><h4>🧑‍⚕️ Patient Explanation</h4>', unsafe_allow_html=True)
            st.write(p_text)
            st.markdown('</div>', unsafe_allow_html=True)

        if c_text:
            st.markdown('<div class="ai-box"><h4>📋 Clinical Explanation</h4>', unsafe_allow_html=True)
            st.write(c_text)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
