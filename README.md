
# Yes or No Tarot

A Streamlit app that draws one random tarot card from the full 78-card deck and returns a clear YES or NO reading.

## Features
- Uniform random selection from all 78 tarot cards
- Each card has a fixed YES or NO meaning
- Reading explanation is under 30 words
- OpenAI as primary model
- Automatic silent fallback to Google Gemini

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your_openai_api_key"
GOOGLE_API_KEY = "your_google_api_key"
```

Run locally:

```bash
streamlit run yes_or_no_tarot.py
```
