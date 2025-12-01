# ============================================================
# Hanvion Health – ICD-10 Explorer (Essential Upgrade Pack)
# Uses: section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx
# ============================================================

import streamlit as st
import pandas as pd
import requests
import re

# ============================================================
# OPTIONAL AI CONFIG (Perplexity)
# ============================================================
PPLX_API_KEY = ""   # <-- Add your Perplexity key here if you want AI
USE_AI = bool(PPLX_API_KEY)


# ============================================================
# 1. LOAD ICD DATA (ROBUST, FLEXIBLE)
# ============================================================
@st.cache_data(show_spinner="Loading ICD-10 dataset…")
def load_icd10():
    file_path = "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx"

    # Load Excel
    try:
        df_raw = pd.read_excel(file_path, dtype=str).fillna("")
    except Exception as e:
        st.error(f"Could not load Excel file: {e}")
        st.stop()

    # Normalize columns for lookup
    cols = {c.lower(): c for c in df_raw.columns}

    def pick_col(*candidates):
        """Return the first matching column in df_raw (case-insensitive), or None."""
        for cand in candidates:
            cand = cand.lower()
            for lc, orig in cols.items():
                if cand in lc:
                    return orig
        return None

    # Try to autodetect useful columns
    code_col = pick_col("code", "icd10", "icd-10", "dx code", "diag code")
    short_col = pick_col("short description", "short_desc", "description", "diag name")
    long_col = pick_col("long description", "long_desc", "full description")
    chapter_col = pick_col("chapter")
    category_col = pick_col("category", "group")

    # Build normalized dataframe
    df = pd.DataFrame()
    df["code"] = df_raw[code_col].astype(str).str.strip() if code_col else ""
    df["description"] = (
        df_raw[short_col].astype(str).str.strip() if short_col else ""
    )
    df["long_description"] = (
        df_raw[long_col].astype(str).str.strip() if long_col else ""
    )
    df["chapter"] = (
        df_raw[chapter_col].astype(str).str.strip() if chapter_col else ""
    )

    if category_col:
        df["category"] = df_raw[category_col].astype(str).str.strip()
    else:
        # Derive category from first 3 characters (e.g., E11)
        df["category"] = df["code"].str.extract(r"^([A-Z]\d{2})", expand=False).fillna("")

    # Drop completely empty codes
    df = df[df["code"] != ""].reset_index(drop=True)

    # Build search blob for ranking
    df["search_blob"] = (
        df["code"].str.upper()
        + " "
        + df["description"].str.upper()
        + " "
        + df["long_description"].str.upper()
        + " "
        + df["chapter"].str.upper()
        + " "
        + df["category"].str.upper()
    )

    return df


# ============================================================
# 2. HANVION THEME (LIGHT + DARK-FRIENDLY)
# ============================================================
def inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 1rem;
        }

        h1, h2, h3, h4 {
            font-weight: 700;
            user-select: none;
        }

        /* Card styling */
        .icd-card {
            background: #faf5ff;
            padding: 18px 20px;
            border-radius: 14px;
            border: 1px solid #e9d5ff;
            margin-bottom: 18px;
        }

        .code-badge {
            background:#6b21a8;
            color:#ffffff;
            padding:4px 10px;
            border-radius:6px;
            font-size:12px;
            font-weight:600;
            display:inline-block;
            margin-bottom:6px;
        }

        .muted {
            color:#6b7280;
            font-size:12px;
        }

        .severity-pill {
            display:inline-block;
            padding:2px 10px;
            border-radius:999px;
            font-size:12px;
            font-weight:500;
        }

        /* Dark mode tweaks */
        @media (prefers-color-scheme: dark) {
            .icd-card {
                background:#020617;
                border-color:#1e293b;
            }
            .muted {
                color:#9ca3af;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 3. SEVERITY METER (HEURISTIC)
# ============================================================
def estimate_severity(code: str, desc: str, long_desc: str):
    """
    Simple rule-based severity estimate for educational display.
    Returns (level:int 1-4, label:str, bar:str)
    """
    text = (desc + " " + long_desc).lower()

    score = 1  # baseline mild

    high_words = [
        "acute", "severe", "malignant", "coma", "respiratory failure",
        "shock", "necrosis", "hemorrhage", "infarction", "crisis"
    ]
    moderate_words = [
        "chronic", "moderate", "exacerbation", "uncontrolled",
        "complication", "with complication"
    ]
    mild_words = ["mild", "unspecified", "without complication"]

    if any(w in text for w in high_words):
        score = 4
    elif any(w in text for w in moderate_words):
        score = 3
    elif any(w in text for w in mild_words):
        score = 2
    else:
        score = 2  # treat unknown as mild–moderate

    if score == 1:
        label = "Low"
        bar = "🟢"
    elif score == 2:
        label = "Mild–Moderate"
        bar = "🟢🟡"
    elif score == 3:
        label = "Moderate–High"
        bar = "🟡🟠"
    else:
        label = "High (depends on context)"
        bar = "🟠🔴"

    return score, label, bar


# ============================================================
# 4. SMART SEARCH & RANKING
# ============================================================
def apply_filters_and_rank(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query:
        # No search – return as-is
        df["rank_score"] = 0
        return df

    q = query.upper().strip()

    scores = []
    for _, row in df.iterrows():
        code = row["code"].upper()
        desc = row["description"].upper()
        longd = row["long_description"].upper()
        cat = row["category"].upper()

        score = 0

        # Strong matches
        if code == q:
            score += 120
        if code.startswith(q):
            score += 80
        if q in desc.split():
            score += 70
        if q in desc:
            score += 50

        # Weaker but useful
        if q in longd:
            score += 25
        if q in cat:
            score += 15

        # If not found anywhere, but present in blob, give tiny score
        if q in row["search_blob"]:
            score += 5

        scores.append(score)

    df = df.copy()
    df["rank_score"] = scores
    df = df[df["rank_score"] > 0].sort_values(
        by=["rank_score", "code"], ascending=[False, True]
    )

    return df


# ============================================================
# 5. AI HELPERS
# ============================================================
def ai_explain(code: str, description: str) -> str:
    if not USE_AI:
        return "AI is disabled. Add PPLX_API_KEY to enable disease explanations."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt = (
            f"Explain ICD-10 code {code}: {description} for a patient in simple terms. "
            "Describe briefly what it means, common symptoms, and when someone should "
            "talk to a doctor. Do not give personalized medical advice."
        )
        payload = {
            "model": "sonar-small-chat",
            "messages": [{"role": "user", "content": prompt}],
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return f"AI error {resp.status_code}. Try again later."

        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return "AI is temporarily unavailable."


def ai_chat(message: str) -> str:
    if not USE_AI:
        return "AI chatbot is disabled (no API key set)."

    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar-small-chat",
            "messages": [{"role": "user", "content": message}],
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return f"AI error {resp.status_code}."
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return "AI is unavailable right now."


# ============================================================
# 6. RENDER CODE CARD
# ============================================================
def render_card(row: pd.Series, full_df: pd.DataFrame):
    code = row["code"]
    desc = row["description"] or "No description available."
    longd = row["long_description"]
    chapter = row["chapter"] or "N/A"
    category = row["category"] or "N/A"

    _, sev_label, sev_bar = estimate_severity(code, desc, longd)

    # Main card
    st.markdown(
        f"""
        <div class="icd-card">
            <div class="code-badge">{code}</div>
            <h3 style="margin-top:6px; margin-bottom:4px;">{desc}</h3>
            <p style="font-size:14px; margin-bottom:6px;">{longd}</p>

            <p class="muted">
                Chapter: {chapter} · Category: {category}
            </p>

            <p class="muted" style="margin-top:4px;">
                Severity (heuristic): <span class="severity-pill">{sev_bar} {sev_label}</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # AI explanation button
    if st.button(f"AI explanation for {code}", key=f"ai_{code}"):
        with st.spinner("Generating educational explanation…"):
            text = ai_explain(code, desc)
        st.info(text)

    # Related code family (same 3-character prefix)
    family_prefix = code[:3]
    with st.expander("Related ICD-10 codes in this family"):
        fam = full_df[full_df["code"].str.startswith(family_prefix)]
        if len(fam) <= 1:
            st.caption("No additional related codes found in this dataset.")
        else:
            for _, r in fam.iterrows():
                if r["code"] == code:
                    continue
                st.write(f"**{r['code']}** – {r['description']}")


# ============================================================
# 7. MAIN APP
# ============================================================
def main():
    inject_css()
    df = load_icd10()

    st.title("Hanvion Health · ICD-10 Explorer")
    st.caption("Search ICD-10 codes, see clinical context, and learn with AI (optional).")

    # -------------------------
    # SEARCH & FILTERS
    # -------------------------
    col_search, col_page = st.columns([3, 1])

    with col_search:
        query = st.text_input(
            "Search by code or diagnosis",
            placeholder="Example: E11, diabetes, asthma, fracture",
        )

    with col_page:
        per_page = st.number_input(
            "Results per page", min_value=5, max_value=100, value=20, step=5
        )

    # Apply search ranking
    if query.strip():
        ranked = apply_filters_and_rank(df, query)
    else:
        ranked = df.copy()
        ranked["rank_score"] = 0

    total = len(ranked)

    if total == 0:
        st.warning("No codes matched your search. Try a different term or fewer filters.")
        return

    total_pages = (total - 1) // per_page + 1
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    start = (page - 1) * per_page
    end = min(start + per_page, total)
    page_df = ranked.iloc[start:end]

    st.caption(f"Showing {start+1}–{end} of {total} matching codes")

    # -------------------------
    # RENDER RESULTS
    # -------------------------
    for _, row in page_df.iterrows():
        render_card(row, df)

    # -------------------------
    # SIMPLE AI CHATBOT
    # -------------------------
    st.markdown("---")
    st.subheader("AI Disease / ICD-10 Chatbot (optional)")

    user_q = st.text_input("Ask a question about a disease, symptom, or ICD-10 code:")
    if user_q:
        with st.spinner("Thinking…"):
            answer = ai_chat(user_q)
        st.write(answer)


if __name__ == "__main__":
    main()
