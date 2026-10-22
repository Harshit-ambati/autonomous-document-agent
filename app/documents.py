"""Deterministic Word rendering; no model-written filenames or executable code."""

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.models import Draft


def clean(text: str) -> str:
    # XML 1.0 forbids most control characters. Keep normal Unicode text intact.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", "", text)


def heading(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", clean(text)).split())


def render_document(draft: Draft, path: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    section.top_margin = section.bottom_margin = Inches(0.8)
    section.left_margin = section.right_margin = Inches(0.85)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.1
    # python-docx's bundled template includes blue paragraph borders on Title.
    for style in doc.styles:
        for border in style.element.findall(".//" + qn("w:pBdr")):
            border.getparent().remove(border)
    for name in ("Title", "Subtitle", "Heading 1", "Heading 2"):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.color.rgb = RGBColor(0, 0, 0)
    doc.styles["Title"].font.size = Pt(26)
    doc.styles["Heading 1"].font.size = Pt(15)
    doc.styles["Heading 1"].paragraph_format.space_before = Pt(15)
    doc.styles["Heading 1"].paragraph_format.keep_with_next = True
    doc.core_properties.title = clean(draft.title)
    doc.core_properties.author = "Document Agent"
    doc.add_paragraph(heading(draft.title), "Title")
    doc.add_paragraph(clean(draft.summary))
    for title, items in (("Planning assumptions", draft.assumptions), ("Constraints and decisions", draft.conflicts)):
        if items:
            doc.add_heading(title, 1)
            for item in items:
                doc.add_paragraph(clean(item), "List Bullet")
    for item in draft.sections:
        doc.add_heading(heading(item.heading), 1)
        for paragraph in item.paragraphs:
            doc.add_paragraph(clean(paragraph))
        for bullet in item.bullets:
            doc.add_paragraph(clean(bullet), "List Bullet")
        for data in item.tables:
            caption = doc.add_paragraph(clean(data.caption))
            caption.paragraph_format.keep_with_next = True
            caption.runs[0].bold = True
            table = doc.add_table(rows=1, cols=len(data.columns))
            table.style = "Table Grid"
            table.autofit = False
            width = (section.page_width - section.left_margin - section.right_margin) // len(data.columns)
            for column in table.columns:
                column.width = width
            repeat = OxmlElement("w:tblHeader")
            table.rows[0]._tr.get_or_add_trPr().append(repeat)
            for cell, label in zip(table.rows[0].cells, data.columns):
                cell.text = clean(label)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "E8EEF4")
                cell._tc.get_or_add_tcPr().append(shading)
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            for row in data.rows:
                for cell, value in zip(table.add_row().cells, row):
                    cell.text = clean(value)
            for row in table.rows:
                row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.space_after = Pt(5)
                        for run in paragraph.runs:
                            run.font.size = Pt(10)
            doc.add_paragraph()
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("Page ").font.size = Pt(9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        doc.save(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
