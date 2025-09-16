"""Streamlit UI helpers for presenting survey results."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from prompt_builder import CATEGORIES

CATEGORY_LABELS = {
    "it_strucnjaci": "IT stručnjaci",
    "nastavnici": "Nastavnici",
    "studenti": "Studenti",
    "uprava": "Uprava",
}


def display_survey_data() -> None:
    """Display survey averages in an organized format."""
    st.markdown("### 📊 Pregled prosječnih ocjena iz upitnika")

    tabs = st.tabs([CATEGORY_LABELS[cat] for cat in CATEGORIES])

    for index, category in enumerate(CATEGORIES):
        with tabs[index]:
            avg_path = Path("averages") / f"{category}_data.json"
            if not avg_path.exists():
                st.error(f"Nema dostupnih podataka za {CATEGORY_LABELS[category]}")
                continue

            with avg_path.open("r", encoding="utf-8") as json_file:
                data = json.load(json_file)

            questions_data = []
            for question_id, average in data["averages"].items():
                question_text = data["question_texts"].get(question_id, "N/A")
                questions_data.append(
                    {
                        "Pitanje ID": question_id,
                        "Tekst pitanja": question_text,
                        "Prosječna ocjena": f"{average:.2f}",
                    }
                )

            df = pd.DataFrame(questions_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            averages_list = list(data["averages"].values())
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Ukupno pitanja", len(averages_list))
            with col2:
                st.metric("Prosječna ocjena", f"{sum(averages_list)/len(averages_list):.2f}")
            with col3:
                st.metric("Najbolja ocjena", f"{max(averages_list):.2f}")
