import random
import streamlit as st
from openai import OpenAI
from google import genai

# -----------------------------------------
# TAROT DECK (78 CARDS)
# Fixed YES/NO meanings based on card index.
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
# CARD IMAGE MAPPING (Rider-Waite, public domain)
# Source: github.com/ekelen/tarot-api
# -----------------------------------------

_BASE_IMG = "https://raw.githubusercontent.com/ekelen/tarot-api/master/public/cards/"

_MAJOR_FILES = {
    "The Fool": "m00.jpg", "The Magician": "m01.jpg",
    "The High Priestess": "m02.jpg", "The Empress": "m03.jpg",
    "The Emperor": "m04.jpg", "The Hierophant": "m05.jpg",
    "The Lovers": "m06.jpg", "The Chariot": "m07.jpg",
    "Strength": "m08.jpg", "The Hermit": "m09.jpg",
    "Wheel of Fortune": "m10.jpg", "Justice": "m11.jpg",
    "The Hanged Man": "m12.jpg", "Death": "m13.jpg",
    "Temperance": "m14.jpg", "The Devil": "m15.jpg",
    "The Tower": "m16.jpg", "The Star": "m17.jpg",
    "The Moon": "m18.jpg", "The Sun": "m19.jpg",
    "Judgement": "m20.jpg", "The World": "m21.jpg",
}

_SUIT_PREFIX = {
    "Wands": "wands", "Cups": "cups",
    "Swords": "swords", "Pentacles": "pents",
}

_RANK_NUM = {
    "Ace": "01", "Two": "02", "Three": "03", "Four": "04", "Five": "05",
    "Six": "06", "Seven": "07", "Eight": "08", "Nine": "09", "Ten": "10",
    "Page": "11", "Knight": "12", "Queen": "13", "King": "14",
}


def get_card_image_url(card_name):
    if card_name in _MAJOR_FILES:
        return _BASE_IMG + _MAJOR_FILES[card_name]
    parts = card_name.split(" of ")
    if len(parts) == 2:
        rank, suit = parts
        prefix = _SUIT_PREFIX.get(suit)
        num = _RANK_NUM.get(rank)
        if prefix and num:
            return _BASE_IMG + f"{prefix}{num}.jpg"
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
[data-testid="stAppViewContainer"] { background-color: #0E0C1A; }
[data-testid="stHeader"]           { background-color: #0E0C1A; }
[data-testid="stSidebar"]          { background-color: #0E0C1A; }

[data-testid="block-container"] {
    padding-top: 2.5rem;
    max-width: 760px;
}

h1 {
    color: #F0EAD6 !important;
    font-size: 2rem !important;
    letter-spacing: 0.05em !important;
    text-align: center !important;
    margin-bottom: 1.5rem !important;
}

label[data-testid="stWidgetLabel"] p {
    color: #C8BFAA !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.03em;
}

[data-testid="stTextInput"] input {
    background-color: #1A1628 !important;
    border: 1px solid #3A3258 !important;
    border-radius: 8px !important;
    color: #F0EAD6 !important;
    font-size: 1rem !important;
}
[data-testid="stTextInput"] input::placeholder { color: #5C5470 !important; }
[data-testid="stTextInput"] input:focus {
    border-color: #C8973A !important;
    box-shadow: 0 0 0 2px rgba(200,151,58,0.25) !important;
}

[data-testid="stButton"] button[kind="primary"] {
    background-color: #C8973A !important;
    border: none !important;
    color: #0E0C1A !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.05em !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    width: 100%;
    transition: background-color 0.2s ease;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #E0AA47 !important;
}

[data-testid="stAlert"] {
    background-color: #251E38 !important;
    border: 1px solid #C8973A !important;
    color: #F0EAD6 !important;
    border-radius: 8px !important;
}

[data-testid="stSpinner"] p { color: #9B84B8 !important; }

[data-testid="stImage"] img {
    border-radius: 12px !important;
    border: 2px solid #C8973A !important;
}

.reading-card {
    background-color: #1A1628;
    border: 1px solid #3A3258;
    border-radius: 14px;
    padding: 1.6rem 1.8rem;
}
.card-drawn-label {
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #9B84B8;
    margin: 0 0 4px;
}
.card-drawn-name {
    font-size: 1.2rem;
    font-weight: 600;
    color: #F0EAD6;
    margin: 0 0 1.1rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #3A3258;
}
.answer-yes {
    font-size: 2.8rem;
    font-weight: 800;
    color: #F4C430;
    letter-spacing: 0.12em;
    margin: 0 0 1rem;
    line-height: 1;
}
.answer-no {
    font-size: 2.8rem;
    font-weight: 800;
    color: #9B84B8;
    letter-spacing: 0.12em;
    margin: 0 0 1rem;
    line-height: 1;
}
.reading-text {
    font-size: 0.95rem;
    color: #C8BFAA;
    font-style: italic;
    line-height: 1.75;
    margin: 0;
}

[data-testid="stMarkdown"] p { color: #C8BFAA !important; }

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
                "<div style='height:300px;background:#1A1628;border:2px solid #C8973A;"
                "border-radius:12px;display:flex;align-items:center;justify-content:center;"
                "color:#5C5470;font-size:2rem;'>🃏</div>",
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

    st.title("🔮 Yes or No Tarot")

    question = st.text_input(
        "Your yes-or-no question",
        placeholder="Will I get the job?",
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
