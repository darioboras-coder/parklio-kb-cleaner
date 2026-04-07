"""
Parklio Knowledge Base Cleaner
==============================
Streamlit web app that converts a Zoho Desk knowledge base CSV export
into a clean English-only Q&A PDF for AI chatbot ingestion.

Deployed on Streamlit Community Cloud. See README.md for deployment steps.
"""

import io
import re
import csv
from pathlib import Path

import streamlit as st
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DetectorFactory.seed = 0


# ---------------------------------------------------------------------------
# Core processing logic (same as kb_to_pdf.py, adapted for in-memory I/O)
# ---------------------------------------------------------------------------
def strip_html(html: str) -> str:
    """Remove HTML tags but keep URLs from <a> and <img> as plain text."""
    if not html:
        return ""
    if "<" not in html:
        return _normalize_whitespace(html)

    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)
        if href and text and href != text:
            a.replace_with(f"{text} ({href})")
        elif href:
            a.replace_with(href)
        else:
            a.replace_with(text)

    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        alt = (img.get("alt") or "").strip()
        if src:
            label = f"[Image: {src}]" if not alt else f"[Image: {alt} - {src}]"
            img.replace_with(label)
        else:
            img.decompose()

    for br in soup.find_all(["br"]):
        br.replace_with("\n")

    return _normalize_whitespace(soup.get_text(" ", strip=False))


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_URL_RE = re.compile(r"https?://\S+|www\.\S+")


def is_english(title: str, answer: str, min_confidence: float = 0.80) -> bool:
    sample = f"{title}. {answer}"
    sample = _URL_RE.sub(" ", sample)
    sample = re.sub(r"[\[\](){}<>]", " ", sample)
    sample = re.sub(r"\s+", " ", sample).strip()

    if len(sample) < 20:
        return all(ord(c) < 128 for c in sample)

    try:
        langs = detect_langs(sample)
    except LangDetectException:
        return False

    if not langs:
        return False
    top = langs[0]
    return top.lang == "en" and top.prob >= min_confidence


def read_csv_bytes(data: bytes):
    """Parse uploaded CSV bytes into normalized rows."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")

    cols = {c.lower().strip(): c for c in reader.fieldnames}
    id_col = cols.get("id")
    title_col = (
        cols.get("article title") or cols.get("title") or cols.get("question")
    )
    answer_col = (
        cols.get("answer") or cols.get("body") or cols.get("content")
    )

    if not title_col or not answer_col:
        raise ValueError(
            f"CSV must contain Title and Answer columns. "
            f"Found columns: {reader.fieldnames}"
        )

    rows = []
    for i, row in enumerate(reader, start=1):
        rows.append(
            {
                "id": (row.get(id_col) or "").strip() if id_col else str(i),
                "title": (row.get(title_col) or "").strip(),
                "answer": (row.get(answer_col) or "").strip(),
            }
        )
    return rows


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_pdf_bytes(entries, source_name: str, min_confidence: float) -> bytes:
    """Build the PDF in memory and return its bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Knowledge Base",
        author="Parklio",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "KBTitle", parent=styles["Title"], fontSize=18, spaceAfter=6
    )
    meta_style = ParagraphStyle(
        "KBMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor="#666666",
        spaceAfter=14,
    )
    q_style = ParagraphStyle(
        "Question",
        parent=styles["Heading3"],
        fontSize=12,
        textColor="#1a3d6d",
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    a_style = ParagraphStyle(
        "Answer",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    story = [
        Paragraph("Knowledge Base", title_style),
        Paragraph(
            f"Source: {source_name} &nbsp;&middot;&nbsp; "
            f"{len(entries)} English entries &nbsp;&middot;&nbsp; "
            f"confidence &ge; {int(min_confidence * 100)}%",
            meta_style,
        ),
    ]

    for n, entry in enumerate(entries, start=1):
        q_text = f"Q{n}: {_xml_escape(entry['title'])}"
        story.append(Paragraph(q_text, q_style))
        answer_html = _xml_escape(entry["answer"]).replace("\n", "<br/>")
        if not answer_html.strip():
            answer_html = "<i>(no answer)</i>"
        story.append(Paragraph(answer_html, a_style))
        story.append(Spacer(1, 2))

    doc.build(story)
    return buf.getvalue()


def process(data: bytes, source_name: str, min_confidence: float):
    raw = read_csv_bytes(data)
    cleaned = []
    skipped_non_english = 0
    skipped_empty = 0

    for row in raw:
        title = row["title"]
        answer = strip_html(row["answer"])
        if not title and not answer:
            skipped_empty += 1
            continue
        if not is_english(title, answer, min_confidence=min_confidence):
            skipped_non_english += 1
            continue
        cleaned.append({"id": row["id"], "title": title, "answer": answer})

    pdf_bytes = build_pdf_bytes(cleaned, source_name, min_confidence)
    return {
        "total": len(raw),
        "kept": len(cleaned),
        "dropped_non_english": skipped_non_english,
        "dropped_empty": skipped_empty,
        "pdf_bytes": pdf_bytes,
        "preview": cleaned[:5],
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Parklio KB Cleaner",
    page_icon="📘",
    layout="centered",
)

st.title("📘 Parklio Knowledge Base Cleaner")
st.write(
    "Upload a Zoho Desk knowledge base CSV export. This tool strips HTML, "
    "filters out non-English entries, and produces a clean Q&A PDF ready "
    "to upload to Chatbase or any other AI chatbot."
)

with st.expander("How it works"):
    st.markdown(
        """
        1. **Upload** your Zoho Desk CSV export. It must contain at least an
           `Article Title` and an `Answer` column.
        2. The tool **strips HTML** from the Answer column while preserving
           any URLs (links and images) as plain text.
        3. It **filters out non-English entries** (Croatian, German, French,
           Italian, Spanish, Polish, Dutch, etc.) using statistical language
           detection.
        4. It produces a **clean Q&A PDF** with `Q1: Title` followed by the
           answer, ready to upload to your AI chatbot.
        """
    )

uploaded = st.file_uploader(
    "Upload your knowledge base CSV",
    type=["csv"],
    help="Export from Zoho Desk → Knowledge Base → Export as CSV",
)

confidence = st.slider(
    "Language detection strictness",
    min_value=0.60,
    max_value=0.95,
    value=0.80,
    step=0.05,
    help=(
        "Higher = stricter (drops more borderline entries). "
        "Lower = more permissive (keeps more, may let some non-English through). "
        "Default 0.80 works well for Parklio's KB."
    ),
)

if uploaded is not None:
    if st.button("Process file", type="primary"):
        with st.spinner("Processing..."):
            try:
                result = process(uploaded.getvalue(), uploaded.name, confidence)
            except Exception as e:
                st.error(f"Failed to process file: {e}")
                st.stop()

        st.success("Done!")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total rows", result["total"])
        col2.metric("Kept (English)", result["kept"])
        col3.metric("Dropped (non-English)", result["dropped_non_english"])
        col4.metric("Dropped (empty)", result["dropped_empty"])

        output_name = Path(uploaded.name).stem + "_filtered.pdf"
        st.download_button(
            label=f"⬇️ Download {output_name}",
            data=result["pdf_bytes"],
            file_name=output_name,
            mime="application/pdf",
            type="primary",
        )

        if result["preview"]:
            with st.expander("Preview first 5 entries"):
                for i, entry in enumerate(result["preview"], start=1):
                    st.markdown(f"**Q{i}: {entry['title']}**")
                    st.write(entry["answer"][:500] + ("..." if len(entry["answer"]) > 500 else ""))
                    st.divider()

st.caption("Built for Parklio · Source CSV stays in your browser session and is not stored.")
