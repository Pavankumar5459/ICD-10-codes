# ============================================================
# HANVION HEALTH • ICD-10 EXPLORER  (Clean UI + Optional AI Chatbot)
# ============================================================

import os
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Optional OpenAI import (app will still work if this fails)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Hanvion Health • ICD-10 Explorer",
    layout="wide",
    page_icon="💠",
)

# Hanvion theme (no emojis, no HTML code leakage)
st.markdown(
    """
<style>
/* Layout */
.block-container {
    max-width: 1100px;
}

/* Hanvion cards */
.han-card {
    background: #faf5ff;
    border: 1px solid #e9d8fd;
    padding: 20px;
    border-radius: 16px;
    margin-top: 18px;
}

/* Code badge */
.code-badge {
    background: #6b46c1;
    color: white;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
}

/* Muted text */
.han-muted {
    color: #6b7280;
    font-size: 13px;
}

/* Headings */
h1, h2, h3 {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATASET (works with your CMS Excel as-is)
# ============================================================
@st.cache_data
def load_data():
    df = pd.read_excel(
        "section111validicd10-jan2026_cms-updates-to-cms-gov.xlsx",
        dtype=str,
    ).fillna("")

    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]

    def pick(*keys):
        """Pick the first column whose name contains any of the given keys."""
        for k in keys:
            for col in df.columns:
                if k in col:
                    return col
        return None

    col_code = pick("code", "icd")
    col_desc = pick("short", "desc")
    col_long = pick("long")
    col_chapter = pick("chapter")
    col_cat = pick("category", "group")

    out = pd.DataFrame()
    out["code"] = df.get(col_code, "")
    out["description"] = df.get(col_desc, "")
    out["long_description"] = df.get(col_long, "")
    out["chapter"] = df.get(col_chapter, "N/A")
    out["category"] = df.get(col_cat, "N/A")

    # Ensure string and no NaN
    out = out.fillna("").astype(str)
    return out


df = load_data()


# ============================================================
# PDF EXPORT
# ============================================================
def build_pdf(row: pd.Series) -> BytesIO:
    """Create a simple 1-page PDF summary for a code."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 50

    def text(t, size=12, bold=False, space=20):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(40, y, t)
        y -= space

    text("Hanvion Health – ICD-10 Summary", 16, True, 30)
    text(f"Code: {row['code']}", 14, True)
    text(f"Description: {row['description']}")
    if row["long_description"]:
        text(f"Details: {row['long_description']}")
    text(f"Chapter: {row['chapter']}   Category: {row['category']}")
    text("For educational use only. Not a substitute for clinical judgment.", 10, False, 40)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ============================================================
# AI CHATBOT HELPER
# ============================================================
def ask_ai_about_code(question: str, row: pd.Series) -> str:
    """
    Answer a question about a specific ICD-10 code.
    Uses OpenAI if configured; otherwise returns a structured fallback message.
    """
    code = row["code"]
    desc = row["description"]
    long_desc = row["long_description"]

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Fallback if OpenAI is not configured
    if not api_key or OpenAI is None:
        lines = [
            "AI chatbot is not configured for this app yet.",
            "",
            "Here is a structured summary instead:",
            f"- ICD-10 code: {code}",
            f"- Name: {desc}",
            f"- Description: {long_desc or 'No additional description available.'}",
            "",
            "For personal medical questions, please speak with a licensed clinician.",
        ]
        return "\n".join(lines)

    # If OpenAI is available, call it safely
    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""
You are an educational medical assistant. Explain ICD-10 code {code}
to a non-technical person in clear, neutral language.

Code: {code}
Short description: {desc}
Long description: {long_desc}

User question:
{question}

Rules:
- Do NOT give treatment instructions or medication doses.
- Do NOT tell the user what they personally should do.
- Emphasize that this is general education, not medical advice.
- If the question is about personal care, tell them to talk to their doctor.
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You provide short, clear, educational explanations about diagnoses. You never give medical advice.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=450,
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        # Graceful error handling
        return (
            "AI error. Showing a basic summary instead.\n\n"
            f"- ICD-10 code: {code}\n"
            f"- Name: {desc}\n"
            f"- Description: {long_desc or 'No additional description available.'}\n\n"
            "Please speak with a clinician for specific medical questions."
        )


# ============================================================
# RENDER ICD CARD (with optional AI section)
# ============================================================
def show_icd_card(row: pd.Series, index: int):
    code = row["code"]
    desc = row["description"]
    long_desc = row["long_description"]

    # Main card container
    st.markdown('<div class="han-card">', unsafe_allow_html=True)

    # Header
    st.markdown(f"<span class='code-badge'>{code}</span>", unsafe_allow_html=True)
    st.markdown(f"### {desc}")
    if long_desc:
        st.markdown(long_desc)

    st.markdown(
        f"<p class='han-muted'>Chapter: {row['chapter']} · Category: {row['category']}</p>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Clinical explanation
    with st.expander("Clinical explanation (educational only)"):
        st.write(
            f"This ICD-10 code is used for documentation and reporting of: **{desc}**. "
            "It helps clinicians and health systems classify this condition consistently."
        )
        if long_desc:
            st.write(f"Additional context: {long_desc}")

    # Patient-friendly explanation (static)
    with st.expander("Patient-friendly summary"):
        st.write(
            "This code is part of your medical record and is mainly used for documentation, "
            "billing, and statistics. It does not by itself describe all details of your health. "
            "Always ask your doctor if you have questions about what this means for you personally."
        )

    # AI chatbot (optional)
    with st.expander("Ask AI about this condition"):
        st.caption("Educational purposes only. This is not medical advice.")
        user_q = st.text_input(
            f"Your question about code {code}",
            key=f"ai_q_{code}_{index}",
            placeholder="Example: What does this diagnosis usually mean?",
        )
        if user_q:
            with st.spinner("Generating educational explanation..."):
                answer = ask_ai_about_code(user_q, row)
            st.write(answer)

    # PDF download
    pdf_buf = build_pdf(row)
    st.download_button(
        "Download summary as PDF",
        data=pdf_buf,
        file_name=f"{code}_summary.pdf",
        mime="application/pdf",
        key=f"pdf_{code}_{index}",
    )


# ============================================================
# MAIN APP
# ============================================================
def main():
    st.title("Hanvion Health • ICD-10 Explorer")
    st.caption("Search ICD codes, view clinical context, and generate summaries. For educational use only.")

    # Search box
    query = st.text_input(
        "Search by ICD code or diagnosis",
        placeholder="Example: E11, diabetes, asthma, fracture",
    )

    # Do NOT show any codes until user searches
    if not query:
        st.info("Start typing above to search ICD-10 codes. No records are shown until you search.")
        return

    # Filter results
    q = query.lower().strip()
    filtered = df[
        df["code"].str.lower().str.contains(q)
        | df["description"].str.lower().str.contains(q)
        | df["long_description"].str.lower().str.contains(q)
    ]

    if filtered.empty:
        st.warning("No matching ICD-10 codes found for your search.")
        return

    # Simple pagination: how many per page
    per_page = st.number_input("Results per page", 5, 100, 20, step=5)
    total = len(filtered)
    max_page = max(1, (total - 1) // per_page + 1)

    page = st.number_input("Page", min_value=1, max_value=max_page, value=1, step=1)

    st.caption(f"Showing {per_page} results per page · {total} total matches")

    start = int((page - 1) * per_page)
    end = int(start + per_page)

    page_df = filtered.iloc[start:end]

    # Show each result
    for i, (_, row) in enumerate(page_df.iterrows()):
        show_icd_card(row, index=start + i)


if __name__ == "__main__":
    main()
