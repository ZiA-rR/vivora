import re
from fpdf import FPDF


def _strip_non_latin(text: str) -> str:
    """fpdf2's built-in fonts are Latin-1 only — drop emojis/non-Latin chars."""
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def viva_to_pdf(markdown_text: str, title: str = "Viva Preparation") -> bytes:
    """Convert the markdown viva-questions output into a styled PDF.

    Note: every multi_cell uses wrapmode="CHAR" so that long unbroken
    tokens (URLs, snake_case_identifiers, etc.) wrap inside the page
    instead of raising FPDFException.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _strip_non_latin(title), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    for raw in markdown_text.split("\n"):
        line = _strip_non_latin(raw.rstrip())

        if not line:
            pdf.ln(3)
            continue

        if line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.ln(3)
            pdf.multi_cell(0, 7, line[3:].strip(), wrapmode="CHAR")
            pdf.ln(1)

        elif line.startswith("**Q") and line.rstrip().endswith("**"):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, line.strip("*").strip(), wrapmode="CHAR")

        elif line.lstrip().startswith(">"):
            pdf.set_font("Helvetica", "I", 10)
            text = line.lstrip(" >").replace("**", "")
            pdf.multi_cell(0, 5, text, wrapmode="CHAR")
            pdf.ln(2)

        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, line.replace("**", ""), wrapmode="CHAR")

    return bytes(pdf.output())
