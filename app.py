import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from markdown_pdf import MarkdownPdf, Section
from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer

from utils import calculate_averages, extract_text_from_pdf

load_dotenv()

API_KEY = st.secrets.get("OPENAI_API_KEY")
MODEL = "gpt-4.1-mini"

if not API_KEY:
    st.error("API key not found.")
    st.stop()

TASK_INSTRUCTIONS = """Na temelju ispunjenih upitnika i dostupnih informacija o visokom učilištu, napišite strukturirani izvještaj analize i preporuka za digitalnu transformaciju tog učilišta.

Izvještaj mora uključivati:
1. SAŽETAK ANALIZE — Kratak pregled stanja digitalne zrelosti učilišta prema rezultatima upitnika u odnosu na strateške ciljeve učilišta (ako su dostupni).
2. KLJUČNI NALAZI — Sažetak slaganja i razlika između strateških ciljeva i rezultata upitnika za svako od šest područja:
   - Vođenje digitalne preobrazbe
   - Digitalne tehnologije u poučavanju i učenju
   - Digitalne tehnologije u istraživanju i suradnji
   - Digitalna infrastruktura i usluge
   - Kibernetička sigurnost
   - Spremnost za umjetnu inteligenciju
3. PREPORUKE ZA DIGITALNU TRANSFORMACIJU — Konkretne preporuke za svako područje, usklađene s nalazima i procjenom trenutnog stanja.
4. ZAKLJUČAK — Završna ocjena stanja i preporuka o prioritetima za daljnji razvoj.

VAŽNO: 
- Nemojte postavljati pitanja niti nuditi dodatne usluge.
- Odgovor mora biti jasan, strukturiran i prilagođen korištenju u formalnom izvještaju.
- Koristite uvid iz upitnika i dostupnih dokumenata za formiranje zaključaka.
- Ne koristiti placeholder dijelove teksta.
"""


def create_pdf_report(content):
    # Create PDF with table of contents
    pdf = MarkdownPdf(toc_level=2, optimize=True)

    # Add title section (not in TOC)
    title_section = f"""# Izvještaj o digitalnoj transformaciji

## Sveučilište Jurja Dobrile u Puli

**Datum:** {datetime.now().strftime("%d.%m.%Y")}

---
"""
    pdf.add_section(Section(title_section, toc=False))

    # Add main content section
    pdf.add_section(Section(content))

    # Set PDF metadata
    pdf.meta["title"] = "Izvještaj o digitalnoj transformaciji"
    pdf.meta["author"] = "Savjetnik za digitalnu transformaciju"
    pdf.meta["subject"] = "Analiza strategije razvoja Sveučilišta Jurja Dobrile u Puli"

    # Save to bytes buffer
    temp_path = f"temp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    try:
        pdf.save(temp_path)
        with open(temp_path, "rb") as f:
            pdf_data = f.read()
        # Clean up temp file
        Path(temp_path).unlink()
        return pdf_data
    except Exception as e:
        # Clean up temp file if it exists
        if Path(temp_path).exists():
            Path(temp_path).unlink()
        raise e


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
    # Initialize session state for analysis results
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

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
            status_text.text("Korak 1/2: Čitanje PDF dokumenta...")
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
            )

            progress_bar.progress(100)
            status_text.text("Analiza završena!")

            # Store results in session state
            st.session_state.analysis_result = response.output_text

        except Exception as e:
            st.error(f"Došlo je do greške pri analizi: {str(e)}")
        finally:
            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()

    # Display analysis results if available
    if st.session_state.analysis_result:
        st.subheader("Izvještaj o digitalnoj transformaciji")
        st.write(st.session_state.analysis_result)

        # PDF export button
        st.subheader("Preuzmi izvještaj")
        try:
            pdf_data = create_pdf_report(st.session_state.analysis_result)
            st.download_button(
                label="📑 Preuzmi kao PDF",
                data=pdf_data,
                file_name=f"izvjestaj_digitalna_transformacija_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key="pdf_download",
            )
        except Exception as e:
            st.error(f"Greška pri kreiranju PDF-a: {str(e)}")

        # Option to clear results
        if st.button("Pokreni novu analizu"):
            st.session_state.analysis_result = None
            st.rerun()


if __name__ == "__main__":
    main()
