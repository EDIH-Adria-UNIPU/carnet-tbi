from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_pdf_viewer import pdf_viewer

from prompt_builder import build_analysis_prompt
from survey_ui import display_survey_data
from utils import extract_text_from_pdf

load_dotenv()

API_KEY = st.secrets.get("OPENAI_API_KEY")
MODEL = "gpt-5"

if not API_KEY:
    st.error("API key not found.")
    st.stop()


def stream_openai_response(
    messages,
    include_pdf,
    include_helsinki,
    include_tartu,
    uploaded_documents=None,
):
    """Generate and stream response from OpenAI API."""
    print(f"Starting chat response generation. Messages count: {len(messages)}")
    client = OpenAI()

    status_placeholder = st.empty()

    if len(messages) == 1:
        print("First message - building full analysis prompt")

        if include_pdf or include_helsinki or include_tartu:
            status_placeholder.markdown("*Čitam dokumente...*")

        user_context = messages[0]["content"]
        full_prompt = build_analysis_prompt(
            user_context,
            include_pdf,
            include_helsinki,
            include_tartu,
            uploaded_documents,
        )
        print(f"Full prompt length: {len(full_prompt)} characters")
        prompt_input = full_prompt
    else:
        print("Follow-up message - using chat history")
        conversation = "Prethodni razgovor:\n"
        for msg in messages:
            conversation += f"{msg['role']}: {msg['content']}\n\n"

        conversation += """Upute za odgovor:
- Odgovorite na korisnikovo najnovije pitanje ili komentar
- Ako korisnik daje nove informacije, kontekst ili uvide koji bi mogli utjecati na analizu, ponudite mu izradu nove/ažurirane analize i preporuka
- Pitajte korisnika: "Želite li da napravim novu analizu i preporuke na temelju ovih novih informacija?"
- Koristite Markdown formatiranje za bolju čitljivost"""

        if uploaded_documents:
            conversation += "\n\nDostupni korisnički PDF dokumenti za kontekst:\n"
            for filename, text in uploaded_documents:
                trimmed_text = text.strip()
                if not trimmed_text:
                    print(f"Skipping empty user document in follow-up: {filename}")
                    continue
                print(
                    "Adding user document to follow-up conversation: "
                    f"{filename} with {len(trimmed_text)} characters"
                )
                conversation += f"[USER PDF] {filename}:\n{trimmed_text}\n\n"

        prompt_input = conversation

    print(f"Using model: {MODEL}")
    status_placeholder.markdown("*Razmišljam...*")

    stream = client.responses.create(
        model=MODEL,
        input=prompt_input,
        reasoning={"effort": "medium"},
        stream=True,
    )

    print("OpenAI stream created successfully")

    content_started = False

    for chunk in stream:
        if hasattr(chunk, "delta") and chunk.delta:
            if not content_started:
                status_placeholder.empty()
                content_started = True
                print("Cleared status indicator, starting content stream")

            yield chunk.delta
        elif hasattr(chunk, "content") and chunk.content:
            if not content_started:
                status_placeholder.empty()
                content_started = True
                print("Cleared status indicator, starting content stream")

            yield chunk.content


def main():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "uploaded_documents" not in st.session_state:
        st.session_state.uploaded_documents = {}

    st.image("assets/carnet.jpg", width=300)
    st.markdown(
        "<h3>Savjetnik za digitalnu transformaciju VU u RH</h3>", unsafe_allow_html=True
    )

    pdf_path = Path("assets") / "strategija_razvoja.pdf"
    pdf_viewer(
        str(pdf_path),
        width=700,
        height=600,
        zoom_level="auto",
        viewer_align="center",
        show_page_separator=True,
    )

    display_survey_data()

    include_pdf = st.toggle(
        "Uključi UNIPU strategiju razvoja u analizu",
        value=True,
    )

    include_helsinki = st.toggle(
        "Uključi strateške dokumente - Sveučilište Helsinki (Finska)",
        value=False,
    )

    include_tartu = st.toggle(
        "Uključi strateške dokumente - Sveučilište Tartu (Estonija)",
        value=False,
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.messages:
        placeholder = (
            'Napišite "Pokreni analizu" za početak ili unesite dodatni kontekst...'
        )
    else:
        placeholder = "Postavite dodatno pitanje..."

    chat_controls = st.container()
    with chat_controls:
        upload_col, input_col = st.columns([1, 5], vertical_alignment="bottom")
        with upload_col:
            with st.popover("📎 Dodaj PDF", use_container_width=True):
                st.markdown("#### Dodajte PDF dokumente")
                st.write(
                    "Sadržaj datoteka bit će dodan u prompt kao korisnički učitani dokument."
                )
                st.file_uploader(
                    "Dodajte vlastite PDF dokumente za kontekst analize",
                    type=["pdf"],
                    accept_multiple_files=True,
                    key="user_pdf_uploader",
                    label_visibility="collapsed",
                )
        with input_col:
            prompt = st.chat_input(placeholder, key="chat_prompt")

    upload_errors: list[str] = []

    uploaded_files = st.session_state.get("user_pdf_uploader")
    current_uploaded_names: set[str] = set()

    if uploaded_files is not None:
        for uploaded_file in uploaded_files:
            current_uploaded_names.add(uploaded_file.name)

            if uploaded_file.name in st.session_state.uploaded_documents:
                continue

            try:
                text = extract_text_from_pdf(uploaded_file)
            except Exception as exc:  # pragma: no cover - streamlit runtime feedback
                error_message = f"Ne mogu pročitati {uploaded_file.name}: {exc}"
                upload_errors.append(error_message)
                print(error_message)
                continue

            if text and text.strip():
                st.session_state.uploaded_documents[uploaded_file.name] = text
            else:
                warning_message = (
                    f"Dokument {uploaded_file.name} ne sadrži čitljiv tekst."
                )
                upload_errors.append(warning_message)
                print(warning_message)

        removed_documents = [
            name
            for name in list(st.session_state.uploaded_documents.keys())
            if name not in current_uploaded_names
        ]

        for name in removed_documents:
            del st.session_state.uploaded_documents[name]

    user_uploaded_documents = list(st.session_state.uploaded_documents.items())

    with chat_controls:
        if user_uploaded_documents:
            st.success(
                "Korisnički PDF dokumenti će biti uključeni u analizu: "
                + ", ".join(doc[0] for doc in user_uploaded_documents)
            )

        if upload_errors:
            for message in upload_errors:
                st.warning(message)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        if prompt.strip():
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                print("Getting OpenAI stream...")
                response = st.write_stream(
                    stream_openai_response(
                        st.session_state.messages,
                        include_pdf,
                        include_helsinki,
                        include_tartu,
                        user_uploaded_documents,
                    )
                )
                print("Stream completed.")

                if not response:
                    response = "Dogodila se greška pri generiranju odgovora."
                    print("No response generated, using fallback")

            except Exception as exc:
                print(f"Error during streaming: {str(exc)}")
                response = f"Greška pri generiranju odgovora: {str(exc)}"
                st.error(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

        if not st.session_state.analysis_complete:
            st.session_state.analysis_complete = True

    if st.session_state.messages:
        st.markdown("---")
        if st.button("Počni novi razgovor"):
            st.session_state.messages = []
            st.session_state.analysis_complete = False
            st.rerun()


if __name__ == "__main__":
    main()
