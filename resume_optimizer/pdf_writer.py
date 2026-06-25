from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.colors import HexColor

# Colors matched to vandana Data Scientist.pdf
NAVY  = HexColor("#152645")   # name + section headers + divider lines
GREY  = HexColor("#555555")   # tagline, dates, contact
BLACK = HexColor("#1a1a1a")   # body text

NAME    = "Vandana Sri Sai Yedla"
CONTACT = "vandanasrisaiyedla@gmail.com  |  (314) 486-5970  |  linkedin.com/in/vandana-yedla"


def _styles():
    return {
        # Header block — centered
        "name":    ParagraphStyle("name",    fontSize=14,  fontName="Helvetica-Bold", textColor=NAVY,  alignment=TA_CENTER, spaceAfter=2),
        "tagline": ParagraphStyle("tagline", fontSize=8.5, fontName="Helvetica",      textColor=GREY,  alignment=TA_CENTER, spaceAfter=1),
        "contact": ParagraphStyle("contact", fontSize=8,   fontName="Helvetica",      textColor=GREY,  alignment=TA_CENTER, spaceAfter=2),
        # Section headers — left-aligned, navy bold
        "hdr":     ParagraphStyle("hdr",     fontSize=9,   fontName="Helvetica-Bold", textColor=NAVY,  spaceBefore=3, spaceAfter=0),
        # Body text
        "body":    ParagraphStyle("body",    fontSize=8,   fontName="Helvetica",      textColor=BLACK, leading=10.5, spaceAfter=1),
        # Bullet points — slightly indented
        "bullet":  ParagraphStyle("bullet",  fontSize=8,   fontName="Helvetica",      textColor=BLACK, leading=10.5, leftIndent=12, firstLineIndent=-9, spaceAfter=0.5),
        # Two-column row helpers
        "bold_l":  ParagraphStyle("bold_l",  fontSize=8,   fontName="Helvetica-Bold", textColor=BLACK, leading=10.5),
        "date_r":  ParagraphStyle("date_r",  fontSize=8,   fontName="Helvetica",      textColor=GREY,  leading=10.5, alignment=TA_RIGHT),
    }


def _top_rule(story):
    """Thin rule separating the header from the body — lighter than section rules."""
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#aaaaaa"), spaceBefore=2, spaceAfter=4))


def _section_rule(story):
    """Navy underline that sits directly below each section header."""
    story.append(HRFlowable(width="100%", thickness=0.6, color=NAVY, spaceBefore=1, spaceAfter=3))


def _two_col(left_para, right_para):
    t = Table([[left_para, right_para]], colWidths=["75%", "25%"])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def write_pdf(data: dict, output_path: str) -> str:
    s = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.55*inch, rightMargin=0.55*inch,
        topMargin=0.35*inch,  bottomMargin=0.35*inch,
    )
    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    story.append(Paragraph(NAME, s["name"]))
    story.append(Paragraph(data.get("title", ""), s["tagline"]))
    story.append(Paragraph(CONTACT, s["contact"]))
    _top_rule(story)

    # ── PROFESSIONAL SUMMARY ─────────────────────────────────────────────────
    story.append(Paragraph("PROFESSIONAL SUMMARY", s["hdr"]))
    _section_rule(story)
    story.append(Paragraph(data.get("summary", ""), s["body"]))

    # ── TECHNICAL SKILLS ─────────────────────────────────────────────────────
    story.append(Paragraph("TECHNICAL SKILLS", s["hdr"]))
    _section_rule(story)
    for grp in data.get("skills", []):
        story.append(Paragraph(f"<b>{grp['category']}:</b> {grp['items']}", s["body"]))

    # ── PROFESSIONAL EXPERIENCE ───────────────────────────────────────────────
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", s["hdr"]))
    _section_rule(story)
    for exp in data.get("experience", []):
        story.append(_two_col(
            Paragraph(f"<b>{exp['title']}</b>  |  {exp['company']}", s["bold_l"]),
            Paragraph(exp.get("dates", ""), s["date_r"]),
        ))
        for b in exp.get("bullets", []):
            story.append(Paragraph(f"• {b}", s["bullet"]))
        story.append(Spacer(1, 2))

    # ── KEY PROJECTS ──────────────────────────────────────────────────────────
    story.append(Paragraph("KEY PROJECTS", s["hdr"]))
    _section_rule(story)
    for proj in data.get("projects", []):
        tech  = proj.get("tech", "")
        label = f"<b>{proj['name']}</b>   <i>({tech})</i>" if tech else f"<b>{proj['name']}</b>"
        story.append(Paragraph(label, s["body"]))
        for b in proj.get("bullets", []):
            story.append(Paragraph(f"• {b}", s["bullet"]))
        story.append(Spacer(1, 1))

    # ── LEADERSHIP & ACHIEVEMENTS ─────────────────────────────────────────────
    if data.get("leadership"):
        story.append(Paragraph("LEADERSHIP & ACHIEVEMENTS", s["hdr"]))
        _section_rule(story)
        for b in data["leadership"]:
            story.append(Paragraph(f"• {b}", s["bullet"]))

    # ── EDUCATION ────────────────────────────────────────────────────────────
    story.append(Paragraph("EDUCATION", s["hdr"]))
    _section_rule(story)
    for edu in data.get("education", []):
        story.append(_two_col(
            Paragraph(f"<b>{edu.get('degree', '')}</b>", s["bold_l"]),
            Paragraph(edu.get("dates", ""), s["date_r"]),
        ))
        story.append(Paragraph(edu.get("school", ""), s["body"]))

    # ── CERTIFICATIONS (appended to education block) ──────────────────────────
    if data.get("certifications"):
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            f"<b>Certifications:</b> {data['certifications']}", s["body"]
        ))

    doc.build(story)
    return output_path
