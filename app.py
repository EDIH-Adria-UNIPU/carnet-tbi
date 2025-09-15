import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer

from utils import calculate_averages, extract_text_from_pdf

load_dotenv()

API_KEY = st.secrets.get("OPENAI_API_KEY")
MODEL = "gpt-5-mini"

if not API_KEY:
    st.error("API key not found.")
    st.stop()

TASK_INSTRUCTIONS = """Visoko učilište: Sveučilište Jurja Dobrile u Puli (UNIPU)

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
- Nemojte postavljati pitanja niti nuditi dodatne usluge.
- Odgovor mora biti jasan, strukturiran i prilagođen korištenju u formalnom izvještaju.
- Koristite uvid iz upitnika i dostupnih dokumenata za formiranje zaključaka.
- Ne koristiti placeholder dijelove teksta.
- Koristite Markdown formatiranje za bolju čitljivost: **podebljani tekst** za važne dijelove, ## za naslove sekcija, - za liste.
"""


def build_analysis_prompt(user_context, include_pdf):
    """Build the full prompt for the initial analysis"""
    print(f"Building analysis prompt. Include PDF: {include_pdf}")
    print(f"User context: {user_context}")

    # Process all categories and get averages
    categories = ["it_strucnjaci", "nastavnici", "studenti", "uprava"]

    # Make sure averages are calculated
    for category in categories:
        json_path = Path("json_data") / f"{category}.json"
        data = calculate_averages(json_path)
        output_dir = Path("averages")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{category}_data.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print("Averages calculated successfully")

    prompt = ""

    # Add PDF content if requested
    if include_pdf:
        print("Including PDF content...")
        pdf_path = Path("assets") / "strategija_razvoja.pdf"
        pdf_text = extract_text_from_pdf(pdf_path)
        prompt += f"Strategija razvoja Sveučilišta Jurja Dobrile u Puli 2021. - 2026:\n{pdf_text}\n\n"
        print("PDF content added successfully")
    else:
        print("Skipping PDF content")

    # Add survey averages
    prompt += "Prosječne ocjene iz upitnika:\n"

    averages = {}
    for category in categories:
        avg_path = Path("averages") / f"{category}_data.json"
        with open(avg_path, "r", encoding="utf-8") as f:
            averages[category] = json.load(f)

    for category, data in averages.items():
        print(f"Processing category: {category}")
        prompt += f"{category}:\n"
        for question_id, average in data["averages"].items():
            question_text = data["question_texts"][question_id]
            prompt += (
                f"{question_id}: {question_text} - Prosječna ocjena: {average:.2f}\n"
            )
        prompt += "\n"

    # Add user context
    if user_context.strip():
        print(f"Adding user context: {user_context.strip()}")
        prompt += f"Kontekst korisnika:\n{user_context.strip()}\n\n"

    prompt += TASK_INSTRUCTIONS
    print(f"Final prompt built with length: {len(prompt)} characters")
    return prompt


def stream_openai_response(messages, include_pdf):
    """Generate and stream response from OpenAI API"""
    print(f"Starting chat response generation. Messages count: {len(messages)}")
    client = OpenAI()

    # Show status indicator
    status_placeholder = st.empty()

    # If this is the first message, build the full analysis prompt
    if len(messages) == 1:
        print("First message - building full analysis prompt")

        # Show document reading indicator if PDF is included
        if include_pdf:
            status_placeholder.markdown("*Čitam dokumente...*")

        user_context = messages[0]["content"]
        full_prompt = build_analysis_prompt(user_context, include_pdf)
        print(f"Full prompt length: {len(full_prompt)} characters")

        # Use single string input for responses API
        prompt_input = full_prompt
    else:
        print("Follow-up message - using chat history")
        # For follow-up messages, build a conversation context with guidance
        conversation = "Prethodni razgovor:\n"
        for msg in messages:
            conversation += f"{msg['role']}: {msg['content']}\n\n"

        # Add instruction for follow-up responses
        conversation += """Upute za odgovor:
- Odgovorite na korisnikovo najnovije pitanje ili komentar
- Ako korisnik daje nove informacije, kontekst ili uvide koji bi mogli utjecati na analizu, ponudite mu izradu nove/ažurirane analize i preporuka
- Pitajte korisnika: "Želite li da napravim novu analizu i preporuke na temelju ovih novih informacija?"
- Koristite Markdown formatiranje za bolju čitljivost"""

        prompt_input = conversation

    print(f"Using model: {MODEL}")

    # Show thinking indicator now that prompt is ready and we're about to call API
    status_placeholder.markdown("*Razmišljam...*")

    # Create streaming response
    stream = client.responses.create(
        model=MODEL,
        input=prompt_input,
        reasoning={"effort": "medium"},
        stream=True,
    )

    print("OpenAI stream created successfully")

    # Track if we've started outputting content (to clear thinking indicator)
    content_started = False

    # Extract text content from stream chunks
    for chunk in stream:
        if hasattr(chunk, "delta") and chunk.delta:
            # Clear status indicator on first content
            if not content_started:
                status_placeholder.empty()
                content_started = True
                print("Cleared status indicator, starting content stream")

            text = chunk.delta
            yield text
        elif hasattr(chunk, "content") and chunk.content:
            # Clear status indicator on first content
            if not content_started:
                status_placeholder.empty()
                content_started = True
                print("Cleared status indicator, starting content stream")

            text = chunk.content
            yield text


def main():
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False

    # Logo and header
    st.image("assets/carnet.jpg", width=300)
    st.markdown(
        "<h3>Savjetnik za digitalnu transformaciju VU u RH</h3>", unsafe_allow_html=True
    )

    # PDF viewer section
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

    # PDF inclusion toggle
    include_pdf = st.toggle(
        "Uključi UNIPU strategiju razvoja u analizu",
        value=True,
    )

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if not st.session_state.messages:
        placeholder = "Postavite pitanje ili unesite dodatni kontekst za analizu..."
    else:
        placeholder = "Postavite dodatno pitanje..."

    if prompt := st.chat_input(placeholder):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            try:
                print("Getting OpenAI stream...")

                # Use st.write_stream with our custom generator
                response = st.write_stream(
                    stream_openai_response(st.session_state.messages, include_pdf)
                )
                print(
                    f"Stream completed. Response length: {len(response) if response else 0}"
                )

                # If no response was generated, fall back
                if not response:
                    response = "Dogodila se greška pri generiranju odgovora."
                    print("No response generated, using fallback")

            except Exception as e:
                print(f"Error during streaming: {str(e)}")
                response = f"Greška pri generiranju odgovora: {str(e)}"
                st.error(response)

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Mark analysis as complete after first response
        if not st.session_state.analysis_complete:
            st.session_state.analysis_complete = True

    # Option to clear chat
    if st.session_state.messages:
        st.markdown("---")
        if st.button("Počni novi razgovor"):
            st.session_state.messages = []
            st.session_state.analysis_complete = False
            st.rerun()


if __name__ == "__main__":
    main()
