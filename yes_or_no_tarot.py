import random
import streamlit as st
from openai import OpenAI
from google import genai

# -----------------------------------------
# TAROT DECK (78 CARDS)
# -----------------------------------------

MAJOR_ARCANA = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World"
]

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]
RANKS = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven",
         "Eight", "Nine", "Ten", "Page", "Knight", "Queen", "King"]

MINOR_ARCANA = [f"{rank} of {suit}" for suit in SUITS for rank in RANKS]
TAROT_DECK = MAJOR_ARCANA + MINOR_ARCANA

CARD_MEANINGS = {
    card: ("YES" if i % 2 == 0 else "NO")
    for i, card in enumerate(TAROT_DECK)
}

# -----------------------------------------
# CARD IMAGE MAPPING
# -----------------------------------------

_BASE_IMG = "https://ishtarcollective.blob.core.windows.net/rider-waite-tarot/"

_MAJOR_INDEX = {
    "The Fool": 0, "The Magician": 1, "The High Priestess": 2,
    "The Empress": 3, "The Emperor": 4, "The Hierophant": 5,
    "The Lovers": 6, "The Chariot": 7, "Strength": 8,
    "The Hermit": 9, "Wheel of Fortune": 10, "Justice": 11,
    "The Hanged Man": 12, "Death": 13, "Temperance": 14,
    "The Devil": 15, "The Tower": 16, "The Star": 17,
    "The Moon": 18, "The Sun": 19, "Judgement": 20, "The World": 21,
}

_SUIT_NAME = {
    "Wands": "wands", "Cups": "cups",
    "Swords": "swords", "Pentacles": "pentacles",
}

_RANK_NUM = {
    "Ace": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
    "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10,
    "Page": 11, "Knight": 12, "Queen": 13, "King": 14,
}


def get_card_image_url(card_name):
    if card_name in _MAJOR_INDEX:
        return _BASE_IMG + f"major-{_MAJOR_INDEX[card_name]}.jpg"
    parts = card_name.split(" of ")
    if len(parts) == 2:
        rank, suit = parts
        suit_str = _SUIT_NAME.get(suit)
        rank_num = _RANK_NUM.get(rank)
        if suit_str and rank_num:
            return _BASE_IMG + f"{suit_str}-{rank_num}.jpg"
    return None


# -----------------------------------------
# SYSTEM PROMPT
# -----------------------------------------

SYSTEM_PROMPT = """
You are a mystical and concise tarot reader for a Yes-or-No tarot app.

You will receive:
1. The user's question.
2. The tarot card drawn.
3. The predetermined answer (YES or NO).

Rules:
- Do not change the selected card.
- Do not change the predetermined YES or NO answer.
- Return only YES or NO. Never MAYBE.
- Write a mystical explanation in 30 words or fewer.
- The explanation should match the card and the predetermined answer.
- Keep the tone magical, insightful, and concise.

Output format:

Card: [Card Name]
Answer: YES or NO
Reading: [30 words or fewer]
""".strip()

# -----------------------------------------
# CUSTOM CSS
# -----------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Raleway:ital,wght@0,300;0,400;0,500;1,300&display=swap');

[data-testid="stAppViewContainer"] { background-color: #0E0C1A; }
[data-testid="stHeader"]           { background-color: #0E0C1A; }
[data-testid="stSidebar"]          { background-color: #0E0C1A; }

/* Centre all block content */
[data-testid="block-container"] {
    padding-top: 3rem;
    max-width: 720px;
    margin: 0 auto;
    text-align: center;
}

/* Push Streamlit's inner columns/widgets back to full width */
[data-testid="stVerticalBlock"] {
    align-items: center;
}

/* Main title */
h1 {
    font-family: 'Cinzel', serif !important;
    color: #F0EAD6 !important;
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-align: center !important;
    margin-bottom: 0.2rem !important;
}

/* Subtitle */
.tarot-subtitle {
    font-family: 'Raleway', sans-serif;
    font-weight: 300;
    font-style: italic;
    font-size: 1rem;
    color: #9B84B8;
    letter-spacing: 0.06em;
    text-align: center;
    margin-bottom: 2rem;
    margin-top: 0;
}

/* Hide the input label */
label[data-testid="stWidgetLabel"] {
    display: none !important;
}

/* Text input */
[data-testid="stTextInput"] input {
    background-color: #1A1628 !important;
    border: 1px solid #3A3258 !important;
    border-radius: 10px !important;
    color: #F0EAD6 !important;
    font-family: 'Raleway', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 400 !important;
    text-align: center !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #5C5470 !important;
    font-style: italic;
    font-family: 'Raleway', sans-serif !important;
}
/* Override Streamlit's red focus — use soft violet instead */
[data-testid="stTextInput"] input:focus {
    border-color: #7C5CBF !important;
    box-shadow: 0 0 0 2px rgba(124, 92, 191, 0.25) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div:focus-within {
    border-color: #7C5CBF !important;
    box-shadow: none !important;
}

/* Button — deep violet, white text */
[data-testid="stButton"] button[kind="primary"] {
    background-color: #5C3D8F !important;
    border: 1px solid #7C5CBF !important;
    color: #F0EAD6 !important;
    font-family: 'Cinzel', serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.1em !important;
    border-radius: 10px !important;
    padding: 0.65rem 2rem !important;
    width: 100%;
    transition: background-color 0.2s ease, border-color 0.2s ease;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #7045AA !important;
    border-color: #9B78D4 !important;
}

/* Warning */
[data-testid="stAlert"] {
    background-color: #251E38 !important;
    border: 1px solid #7C5CBF !important;
    color: #F0EAD6 !important;
    border-radius: 8px !important;
    font-family: 'Raleway', sans-serif !important;
}

/* Spinner */
[data-testid="stSpinner"] p {
    color: #9B84B8 !important;
    font-family: 'Raleway', sans-serif !important;
}

/* Card image */
[data-testid="stImage"] img {
    border-radius: 12px !important;
    border: 2px solid #7C5CBF !important;
}

/* Reading card */
.reading-card {
    background-color: #1A1628;
    border: 1px solid #3A3258;
    border-radius: 14px;
    padding: 1.8rem 2rem;
    text-align: left;
}
.card-drawn-label {
    font-family: 'Raleway', sans-serif;
    font-size: 0.65rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #7C5CBF;
    margin: 0 0 5px;
}
.card-drawn-name {
    font-family: 'Cinzel', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: #F0EAD6;
    margin: 0 0 1.1rem;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid #2E2540;
}
.answer-yes {
    font-family: 'Cinzel', serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #F4C430;
    letter-spacing: 0.14em;
    margin: 0 0 1rem;
    line-height: 1;
}
.answer-no {
    font-family: 'Cinzel', serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #9B84B8;
    letter-spacing: 0.14em;
    margin: 0 0 1rem;
    line-height: 1;
}
.reading-text {
    font-family: 'Raleway', sans-serif;
    font-size: 0.95rem;
    font-style: italic;
    font-weight: 300;
    color: #C8BFAA;
    line-height: 1.8;
    margin: 0;
}

[data-testid="stMarkdown"] p {
    color: #C8BFAA !important;
    font-family: 'Raleway', sans-serif !important;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0E0C1A; }
::-webkit-scrollbar-thumb { background: #3A3258; border-radius: 3px; }
</style>
"""

# -----------------------------------------
# HELPERS
# -----------------------------------------

def draw_random_card():
    card = random.choice(TAROT_DECK)
    answer = CARD_MEANINGS[card]
    return card, answer


def generate_with_openai(question, card, answer):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    user_prompt = f"Question: {question}\nCard: {card}\nPredetermined Answer: {answer}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content.strip()


def extract_gemini_text(response):
    if hasattr(response, "text") and response.text:
        return response.text.strip()
    text = ""
    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
    return text.strip()


def generate_with_gemini(question, card, answer):
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    user_prompt = f"Question: {question}\nCard: {card}\nPredetermined Answer: {answer}"
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[SYSTEM_PROMPT, user_prompt]
    )
    return extract_gemini_text(response)


def generate_reading(question, card, answer):
    try:
        return generate_with_openai(question, card, answer)
    except Exception:
        return generate_with_gemini(question, card, answer)


def parse_reading(raw_text):
    card_name, answer, reading = "", "", ""
    for line in raw_text.strip().splitlines():
        if line.lower().startswith("card:"):
            card_name = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("answer:"):
            answer = line.split(":", 1)[-1].strip().upper()
        elif line.lower().startswith("reading:"):
            reading = line.split(":", 1)[-1].strip()
    return card_name, answer, reading


def render_reading(card_name, answer, reading, image_url):
    col_img, col_text = st.columns([1, 1.4], gap="large")

    with col_img:
        if image_url:
            st.image(image_url, use_container_width=True)
        else:
            st.markdown(
                "<div style='height:300px;background:#1A1628;border:2px solid #7C5CBF;"
                "border-radius:12px;display:flex;align-items:center;justify-content:center;"
                "color:#3A3258;font-size:2rem;'>🃏</div>",
                unsafe_allow_html=True,
            )

    with col_text:
        answer_class = "answer-yes" if answer == "YES" else "answer-no"
        st.markdown(
            f"""
            <div class="reading-card">
                <p class="card-drawn-label">Card drawn</p>
                <p class="card-drawn-name">{card_name}</p>
                <p class="{answer_class}">{answer}</p>
                <p class="reading-text">{reading}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------------------
# MAIN
# -----------------------------------------

def main():
    st.set_page_config(
        page_title="Yes or No Tarot",
        page_icon="🔮",
        layout="centered",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if "has_drawn" not in st.session_state:
        st.session_state.has_drawn = False
    if "result" not in st.session_state:
        st.session_state.result = None

    # Title + subtitle
    st.title("🔮 Yes or No Tarot")
    st.markdown(
        '<p class="tarot-subtitle">The cards are listening. Ask what your heart seeks.</p>',
        unsafe_allow_html=True,
    )

    # Input — label hidden via CSS, label_visibility also collapsed for safety
    question = st.text_input(
        "question",
        placeholder="Ask away...",
        label_visibility="collapsed",
    )

    btn_label = "✨ Draw Another Card" if st.session_state.has_drawn else "✨ Draw a Card"

    if st.button(btn_label, type="primary"):
        if not question.strip():
            st.warning("Please enter a question first.")
        else:
            card, answer = draw_random_card()
            image_url = get_card_image_url(card)

            with st.spinner("Consulting the cards..."):
                try:
                    raw = generate_reading(question.strip(), card, answer)
                    card_name, parsed_answer, reading = parse_reading(raw)
                    if not card_name:
                        card_name = card
                    if not parsed_answer:
                        parsed_answer = answer
                    if not reading:
                        reading = raw
                except Exception:
                    card_name = card
                    parsed_answer = answer
                    reading = (
                        f"The card speaks clearly. "
                        f"Its energy points firmly toward {answer.lower()}."
                    )

            st.session_state.result = {
                "card_name": card_name,
                "answer": parsed_answer,
                "reading": reading,
                "image_url": image_url,
            }
            st.session_state.has_drawn = True

    if st.session_state.result:
        r = st.session_state.result
        render_reading(r["card_name"], r["answer"], r["reading"], r["image_url"])


if __name__ == "__main__":
    main()
