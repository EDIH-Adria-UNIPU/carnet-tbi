"""Utilities for preparing the analysis prompt sent to the OpenAI API."""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from utils import calculate_averages, extract_text_from_pdf

CATEGORIES = ["it_strucnjaci", "nastavnici", "studenti", "uprava"]

HELSINKI_DOCS = [
    ("helsinki_strategy.pdf", "Helsinki Strategy Document"),
    ("helsinki_it2030.pdf", "Helsinki IT2030 Document"),
]

TARTU_DOCS = [
    ("tartu_strategy.pdf", "Tartu Strategy Document"),
    ("tartu_action_plan.pdf", "Tartu Action Plan Document"),
]


def get_task_instructions(include_helsinki: bool, include_tartu: bool) -> str:
    """Return base instructions with optional comparative analysis guidance."""
    base_instructions = """Visoko učilište: Sveučilište Jurja Dobrile u Puli (UNIPU)

Na temelju ispunjenih upitnika i dostupnih informacija o visokom učilištu, napišite strukturirani izvještaj analize i preporuka za digitalnu transformaciju tog učilišta.

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
- U slučaju da je korisnik pružio dodatne upute ili kontekst, prati upute korisnika.
- Nemoj koristiti placeholdere.
- Nemojte postavljati pitanja niti nuditi dodatne usluge.
- Odgovor mora biti jasan, strukturiran i prilagođen korištenju u formalnom izvještaju.
- Koristite Markdown formatiranje za bolju čitljivost: **podebljani tekst** za važne dijelove, ## za naslove sekcija, - za liste."""

    if include_helsinki or include_tartu:
        base_instructions += """

DODATNE UPUTE ZA KOMPARATIVNU ANALIZU:
- Analizirajte i usporedite strateške pristupe UNIPU-a s pristupima drugih sveučilišta.
- Identificirajte najbolje prakse iz strategija drugih sveučilišta koje bi mogle biti primjenjive na UNIPU.
- U preporukama eksplicitno navedite primjere iz strategija drugih sveučilišta kada su relevantni.
- Koristite fraze poput "Prema iskustvu Sveučilišta Helsinki..." ili "Sveučilište Tartu je uspješno implementiralo..." kada citirate najbolje prakse.
- Fokusirajte se na praktične i izvodljive prijedloge temeljene na dokazanim uspješnim pristupima."""

    return base_instructions


def _ensure_survey_averages() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Recalculate survey averages and return their JSON payloads."""
    averages_dir = Path("averages")
    averages_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Dict[str, Dict[str, float]]] = {}
    for category in CATEGORIES:
        json_path = Path("json_data") / f"{category}.json"
        data = calculate_averages(json_path)
        output_path = averages_dir / f"{category}_data.json"
        with output_path.open("w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=2)
        results[category] = data

    return results


def _append_document_texts(prompt: str, documents: list[tuple[str, str]]) -> str:
    """Concatenate document texts into the prompt if the files exist."""
    for filename, title in documents:
        doc_path = Path("assets") / Path(filename)
        if not doc_path.exists():
            print(f"Warning: {doc_path} not found")
            continue

        doc_text = extract_text_from_pdf(doc_path)
        prompt += f"{title}:\n{doc_text}\n\n"
        print(f"Added {title}")

    return prompt


def _append_nested_document_texts(
    prompt: str, documents: list[tuple[str, str]], subfolder: str
) -> str:
    """Helper for Helsinki/Tartu docs that live inside a subfolder."""
    resolved = []
    for filename, title in documents:
        resolved.append((str(Path(subfolder) / filename), title))
    return _append_document_texts(prompt, resolved)


def build_analysis_prompt(
    user_context: str,
    include_pdf: bool,
    include_helsinki: bool,
    include_tartu: bool,
    uploaded_documents: List[Tuple[str, str]] | None = None,
) -> str:
    """Compose the full prompt for the initial analysis call."""
    print(
        "Building analysis prompt. "
        f"Include PDF: {include_pdf}, Include Helsinki: {include_helsinki}, Include Tartu: {include_tartu}"
    )
    print(f"User context: {user_context}")

    survey_averages = _ensure_survey_averages()
    print("Averages calculated successfully")

    prompt = ""

    user_docs = uploaded_documents or []

    if include_pdf:
        print("Including PDF content...")
        pdf_path = Path("assets") / "strategija_razvoja.pdf"
        pdf_text = extract_text_from_pdf(pdf_path)
        prompt += (
            "Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026:\n"
            f"{pdf_text}\n\n"
        )
        print("PDF content added successfully")
    else:
        print("Skipping PDF content")

    if user_docs:
        print(f"Including {len(user_docs)} user-uploaded documents")
        prompt += "Korisnički učitani dokumenti (označeno kao [USER PDF]):\n"
        for filename, text in user_docs:
            trimmed_text = text.strip()
            if not trimmed_text:
                print(f"Skipping empty user document: {filename}")
                continue
            print(
                f"Adding user document: {filename} with {len(trimmed_text)} characters"
            )
            prompt += f"[USER PDF] {filename}:\n{trimmed_text}\n\n"

    if include_helsinki:
        print("Including Helsinki documents...")
        prompt = _append_nested_document_texts(prompt, HELSINKI_DOCS, "Helsinki")

    if include_tartu:
        print("Including Tartu documents...")
        prompt = _append_nested_document_texts(prompt, TARTU_DOCS, "Tartu")

    prompt += "Prosječne ocjene iz upitnika:\n"

    for category, data in survey_averages.items():
        print(f"Processing category: {category}")
        prompt += f"{category}:\n"
        for question_id, average in data["averages"].items():
            question_text = data["question_texts"][question_id]
            prompt += (
                f"{question_id}: {question_text} - Prosječna ocjena: {average:.2f}\n"
            )
        prompt += "\n"

    if user_context and user_context.strip():
        context = user_context.strip()
        print(f"Adding user context: {context}")
        prompt += f"Kontekst/upute korisnika:\n{context}\n\n"
    else:
        print("No user context provided - proceeding with standard analysis")

    prompt += get_task_instructions(include_helsinki, include_tartu)
    print(f"Final prompt built with length: {len(prompt)} characters")
    return prompt
