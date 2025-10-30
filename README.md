# CARNET TBI

Sustav za analizu digitalne zrelosti visokoobrazovnih institucija s AI-powered preporukama za digitalnu transformaciju.

## Pokretanje

1. Instaliraj [uv](https://github.com/astral-sh/uv) (Python package manager)

2. Konfiguriraj OpenAI API ključ:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Uredi `.streamlit/secrets.toml` i dodaj svoj OpenAI API ključ

3. Pokreni aplikaciju:
   ```bash
   uv run streamlit run app.py
   ```

## Funkcionalnosti

- **Pregled anketa**: Prikaz agregiranih rezultata anketa od IT osoblja, nastavnika, studenata i uprave
- **AI analiza**: AI preporuke za digitalnu transformaciju bazirane na rezultatima anketa i institucionalnoj strategiji
- **Usporedba strategija**: Usporedba sa strategijama sveučilišta u Helsinkiju i Tartuu
- **PDF izvještaji**: Izvoz razgovora i analiza u PDF format