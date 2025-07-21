import json
from pathlib import Path
import io
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from utils import calculate_averages, extract_text_from_pdf

load_dotenv()

API_KEY = st.secrets.get("OPENAI_API_KEY")
MODEL = "gpt-4.1-mini"

if not API_KEY:
    st.error("API key not found.")
    st.stop()

TASK_INSTRUCTIONS = """Na temelju danih informacija, napišite detaljnu analizu i preporuke za digitalnu transformaciju visokog učilišta.

Usporedite ciljeve i planove iz strategije razvoja s rezultatima upitnika. Identificirajte područja gdje postoji slaganje ili razlike između planiranih aktivnosti i percepcije sudionika. 

VAŽNO: Odgovorite u obliku strukturiranog izvještaja s naslovovima i podnaslovovima. Ne postavljajte pitanja na kraju niti nudite dodatne usluge. Završite izvještaj konkretnim preporukama.

Struktura izvještaja:
1. SAŽETAK ANALIZE
2. KLJUČNI NALAZI
3. PREPORUKE ZA DIGITALNU TRANSFORMACIJU
4. ZAKLJUČAK"""

# Process all categories and save results
categories = ["it_strucnjaci", "nastavnici", "studenti", "uprava"]
for category in categories:
    json_path = Path("json_data") / f"{category}.json"
    data = calculate_averages(json_path)
    output_dir = Path("averages")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{category}_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    st.image("assets/carnet.jpg", width=300)
    st.markdown(
        "<h3>Savjetnik za digitalnu transformaciju VU u RH</h3>", unsafe_allow_html=True
    )
    st.write(
        "Analiza je temeljena na dokumentu: [Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026.]"
    )

    # PDF viewer section
    st.subheader("Pregled dokumenta")
    pdf_path = Path("assets") / "strategija_razvoja.pdf"

    # Display PDF with custom options
    pdf_viewer(
        str(pdf_path),
        width=700,
        height=600,
        zoom_level="auto",
        viewer_align="center",
        show_page_separator=True,
    )

    if st.button("Pokreni analizu"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Extract PDF text
            status_text.text("Korak 1/2: Učitavanje PDF dokumenta...")
            progress_bar.progress(50)
            pdf_path = Path("assets") / "strategija_razvoja.pdf"
            pdf_text = extract_text_from_pdf(pdf_path)

            print("PDF text extracted successfully.")

            # Load averages and question texts
            averages = {}
            for category in categories:
                avg_path = Path("averages") / f"{category}_data.json"
                with open(avg_path, "r", encoding="utf-8") as f:
                    averages[category] = json.load(f)

            print("Averages loaded successfully.")

            # Prepare prompt for OpenAI
            prompt = f"Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026:\n{pdf_text}\n\n"
            prompt += "Prosječne ocjene iz upitnika:\n"
            for category, data in averages.items():
                print(f"Processing category: {category}")
                prompt += f"{category}:\n"
                for question_id, average in data["averages"].items():
                    question_text = data["question_texts"][question_id]
                    prompt += f"{question_id}: {question_text} - Prosječna ocjena: {average:.2f}\n"
                prompt += "\n"

            prompt += TASK_INSTRUCTIONS

            # Generate analysis
            status_text.text("Korak 2/2: Generiranje analize...")
            client = OpenAI()

            print("Using model:", MODEL)

            response = client.responses.create(
                model=MODEL,
                input=prompt,
                temperature=0.5,
            )

            progress_bar.progress(100)
            status_text.text("Analiza završena!")

            # Display results
            st.subheader("Izvještaj o digitalnoj transformaciji")
            st.write(response.output_text)

        except Exception as e:
            st.error(f"Došlo je do greške pri analizi: {str(e)}")
        finally:
            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()


if __name__ == "__main__":
    main()
