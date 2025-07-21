import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from utils import calculate_averages, extract_text_from_pdf

load_dotenv()

API_KEY = st.secrets.get("OPENAI_API_KEY")

if not API_KEY:
    st.error("API key not found.")
    st.stop()


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
    st.title("Savjetnik za digitalnu transformaciju visokih učilišta u RH")
    st.write(
        "Analiza strategije razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026."
    )
    st.write(
        "Analiza je temeljena na dokumentu: [Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026.]"
    )

    if st.button("Pokreni analizu"):
        with st.spinner("Analiza u tijeku..."):
            # Extract PDF text
            pdf_path = Path("assets") / "strategija_razvoja.pdf"
            pdf_text = extract_text_from_pdf(pdf_path)

            # Load averages and question texts
            averages = {}
            for category in categories:
                avg_path = Path("averages") / f"{category}_data.json"
                with open(avg_path, "r", encoding="utf-8") as f:
                    averages[category] = json.load(f)

            # Prepare prompt for OpenAI
            prompt = f"Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026:\n{pdf_text}\n\n"
            prompt += "Prosječne ocjene iz upitnika:\n"
            for category, data in averages.items():
                prompt += f"{category}:\n"
                for question_id, average in data["averages"].items():
                    question_text = data["question_texts"][question_id]
                    prompt += f"{question_id}: {question_text} - Prosječna ocjena: {average:.2f}\n"
                prompt += "\n"
            prompt += "Na temelju danih informacija, dajte preporuke za digitalnu transformaciju visokog učilišta."

            client = OpenAI()

            try:
                response = client.responses.create(
                    model="gpt-4.1-nano",
                    input=prompt,
                    temperature=0.5,
                )
                st.write(response.output_text)
            except Exception as e:
                st.error(f"Došlo je do greške pri analizi: {str(e)}")


if __name__ == "__main__":
    main()
