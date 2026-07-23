from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.dml.color import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output" / "pdf" / "DataVerse_AI_Final_Report_Latest_Architecture_2026.docx"
OUTPUT = ROOT / "output" / "pdf" / "DataVerse_AI_Final_Report_Black_Text_2026.docx"
BLACK = "000000"


def set_run_element_black(run_element) -> None:
    run_properties = run_element.get_or_add_rPr()
    color = run_properties.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        run_properties.append(color)
    color.set(qn("w:val"), BLACK)
    for attribute in ("themeColor", "themeTint", "themeShade"):
        qualified = qn(f"w:{attribute}")
        if qualified in color.attrib:
            del color.attrib[qualified]


def make_text_black() -> None:
    document = Document(SOURCE)

    for style in document.styles:
        try:
            style.font.color.rgb = RGBColor(0, 0, 0)
        except (AttributeError, ValueError):
            continue

    parts = [document.part]
    for section in document.sections:
        parts.extend(
            [
                section.header.part,
                section.first_page_header.part,
                section.even_page_header.part,
                section.footer.part,
                section.first_page_footer.part,
                section.even_page_footer.part,
            ]
        )

    seen_parts: set[int] = set()
    for part in parts:
        if id(part) in seen_parts:
            continue
        seen_parts.add(id(part))
        for run_element in part.element.xpath(".//w:r"):
            set_run_element_black(run_element)

    document.core_properties.title = "DataVerse AI Final Report - Black Text 2026"
    document.core_properties.subject = "Latest architecture with black headings and body text"
    document.save(OUTPUT)
    print(f"black_text_document={OUTPUT}")


if __name__ == "__main__":
    make_text_black()
