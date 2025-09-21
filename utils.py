import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Union

import pdfplumber
from markdown_pdf import MarkdownPdf, Section


# Function to calculate averages and extract question texts
def calculate_averages(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    question_sums = {}
    question_counts = {}
    question_texts = {}

    for responder in data:
        for response in responder["Responses"]:
            question_id = response["Question_ID"]
            answer = response["Answer"]
            if question_id not in question_sums:
                question_sums[question_id] = 0
                question_counts[question_id] = 0
                question_texts[question_id] = response["Question_Text"]
            question_sums[question_id] += answer
            question_counts[question_id] += 1

    averages = {}
    for question_id in question_sums:
        averages[question_id] = (
            question_sums[question_id] / question_counts[question_id]
        )

    return {"averages": averages, "question_texts": question_texts}


# Function to extract text from PDF
def extract_text_from_pdf(pdf_source: Union[str, Path, BinaryIO]):
    """Return extracted text from a PDF path or binary stream."""

    if isinstance(pdf_source, (str, Path)):
        open_target = pdf_source
    else:
        pdf_source.seek(0)
        open_target = pdf_source

    with pdfplumber.open(open_target) as pdf:
        text = ""
        for page in pdf.pages:
            text += (
                page.extract_text() or ""
            )  # Handle cases where extract_text() returns None
    return text


def convert_conversation_to_markdown(messages: list[dict]) -> str:
    """Convert conversation messages to markdown format."""

    if not messages:
        return "# Razgovor\n\nNema poruka za izvoz."

    # Header with timestamp
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    markdown_content = f"""# Razgovor sa Savjetnikom za digitalnu transformaciju

**Datum izvoza:** {timestamp}

---

"""

    # Convert each message
    for i, message in enumerate(messages, 1):
        role = message.get("role", "")
        content = message.get("content", "")

        # Format role names
        if role == "user":
            role_name = "👤 **Korisnik**"
        elif role == "assistant":
            role_name = "**Savjetnik**"
        else:
            role_name = f"**{role.title()}**"

        # Add message to markdown
        markdown_content += f"""## Poruka {i}

{role_name}

{content}

---

"""

    return markdown_content


def generate_conversation_pdf(messages: list[dict]) -> bytes:
    """Generate PDF from conversation messages."""
    import os

    # Convert to markdown
    markdown_content = convert_conversation_to_markdown(messages)

    # Create PDF using markdown-pdf
    pdf = MarkdownPdf(toc_level=2)
    pdf.add_section(Section(markdown_content))

    # Generate PDF to temporary file and read bytes
    tmp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_file_path = tmp_file.name
    tmp_file.close()  # Close the file handle immediately

    try:
        # Save PDF to the temporary file path
        pdf.save(tmp_file_path)

        # Read the PDF file as bytes
        with open(tmp_file_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        return pdf_bytes
    finally:
        # Clean up the temporary file
        try:
            os.unlink(tmp_file_path)
        except (OSError, PermissionError):
            # If we can't delete it immediately, it will be cleaned up later
            pass
