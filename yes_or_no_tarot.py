import io
import math
import random

import streamlit as st
from openai import OpenAI
from google import genai
from PIL import Image, ImageDraw, ImageFont

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
TAROT_DECK   = MAJOR_ARCANA + MINOR_ARCANA

CARD_MEANINGS = {
    card: ("YES" if i % 2 == 0 else "NO")
    for i, card in enumerate(TAROT_DECK)
}

_MAJOR_INDEX = {card: i for i, card in enumerate(MAJOR_ARCANA)}
_RANK_NUM = {
    "Ace": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
    "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10,
    "Page": 11, "Knight": 12, "Queen": 13, "King": 14,
}

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
# CARD IMAGE GENERATION (PIL — always works)
# -----------------------------------------

def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _load_fonts():
    """Try serif fonts in order; fall back to PIL default."""
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        "/usr/local/share/fonts/LiberationSerif-Bold.ttf",
    ]
    candidates_italic = [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]
    bold_path   = next((p for p in candidates        if __import__('os').path.exists(p)), None)
    italic_path = next((p for p in candidates_italic if __import__('os').path.exists(p)), None)

    def tf(path, size):
        try:
            return ImageFont.truetype(path, size) if path else ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    return (
        tf(bold_path, 26),   # title
        tf(bold_path, 20),   # subtitle / rank
        tf(italic_path, 14), # label
    )


def _draw_pip(draw, cx, cy, suit, size=20, color=(200, 151, 58)):
    s = size
    if suit == "Wands":
        draw.line([(cx, cy - s), (cx, cy + s)], fill=color, width=2)
        draw.line([(cx - s // 2, cy - s // 3), (cx + s // 2, cy - s // 3)], fill=color, width=2)
    elif suit == "Cups":
        pts = [(cx - s // 2, cy - s // 2), (cx + s // 2, cy - s // 2),
               (cx + s // 3, cy + s // 2), (cx - s // 3, cy + s // 2)]
        draw.polygon(pts, outline=color, fill=None)
    elif suit == "Swords":
        draw.polygon([(cx, cy - s), (cx + s // 3, cy), (cx, cy + s), (cx - s // 3, cy)],
                     outline=color, fill=None)
    elif suit == "Pentacles":
        draw.ellipse([cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2],
                     outline=color, width=2)


_PIP_LAYOUTS = {
    1:  [(0, 0)],
    2:  [(0, -60), (0, 60)],
    3:  [(0, -60), (0, 0), (0, 60)],
    4:  [(-50, -55), (50, -55), (-50, 55), (50, 55)],
    5:  [(-50, -55), (50, -55), (0, 0), (-50, 55), (50, 55)],
    6:  [(-50, -65), (50, -65), (-50, 0), (50, 0), (-50, 65), (50, 65)],
    7:  [(-50, -70), (50, -70), (-50, -20), (50, -20), (0, 20), (-50, 65), (50, 65)],
    8:  [(-50, -70), (50, -70), (-50, -20), (50, -20),
         (-50, 30), (50, 30), (-50, 75), (50, 75)],
    9:  [(-50, -75), (50, -75), (-50, -30), (50, -30), (0, 0),
         (-50, 30), (50, 30), (-50, 75), (50, 75)],
    10: [(-50, -80), (50, -80), (-50, -40), (50, -40), (-50, 0), (50, 0),
         (-50, 40), (50, 40), (-50, 80), (50, 80)],
}

_ROMAN = {0:"0",1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",8:"VIII",
          9:"IX",10:"X",11:"XI",12:"XII",13:"XIII",14:"XIV",15:"XV",
          16:"XVI",17:"XVII",18:"XVIII",19:"XIX",20:"XX",21:"XXI"}

_RANK_LABEL = {1:"ACE",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",
               8:"VIII",9:"IX",10:"X",11:"PAGE",12:"KNIGHT",13:"QUEEN",14:"KING"}

_RANK_NAME  = {1:"Ace",2:"Two",3:"Three",4:"Four",5:"Five",6:"Six",7:"Seven",
               8:"Eight",9:"Nine",10:"Ten",11:"Page",12:"Knight",13:"Queen",14:"King"}

_SUIT_COLOR = {
    "Wands":     _hex('#C8973A'),
    "Cups":      _hex('#7C5CBF'),
    "Swords":    _hex('#9B84B8'),
    "Pentacles": _hex('#5DCAA5'),
}


@st.cache_data(show_spinner=False)
def make_card_image(card_name: str) -> io.BytesIO:
    W, H = 350, 600
    BG    = _hex('#0E0C1A')
    CARD  = _hex('#1A1628')
    GOLD  = _hex('#C8973A')
    VIO   = _hex('#3A3258')
    PALE  = _hex('#F0EAD6')
    MID   = _hex('#9B84B8')

    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Card body + borders
    draw.rounded_rectangle([12, 12, W-13, H-13], radius=14, fill=CARD)
    draw.rounded_rectangle([12, 12, W-13, H-13], radius=14, outline=GOLD, width=2)
    draw.rounded_rectangle([22, 22, W-23, H-23], radius=10, outline=VIO,  width=1)

    # Corner diamonds
    for cx_, cy_ in [(42, 42), (W-42, 42), (42, H-42), (W-42, H-42)]:
        s = 7
        draw.polygon([(cx_,cy_-s),(cx_+s,cy_),(cx_,cy_+s),(cx_-s,cy_)], fill=GOLD)

    f_title, f_rank, f_label = _load_fonts()

    cx = W // 2

    # Dividers
    for y_ in [140, 420]:
        draw.line([(50, y_), (W-50, y_)], fill=VIO, width=1)

    # ---- MAJOR ARCANA ----
    if card_name in _MAJOR_INDEX:
        idx = _MAJOR_INDEX[card_name]
        draw.text((cx, 90), _ROMAN[idx], font=f_rank, fill=GOLD, anchor='mm')

        # Six-spoked star in circle
        cy_c = 280
        r = 85
        draw.ellipse([cx-r, cy_c-r, cx+r, cy_c+r], outline=VIO, width=1)
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            x1 = cx + 28 * math.cos(angle)
            y1 = cy_c + 28 * math.sin(angle)
            x2 = cx + 68 * math.cos(angle)
            y2 = cy_c + 68 * math.sin(angle)
            draw.line([x1, y1, x2, y2], fill=GOLD, width=1)
        draw.ellipse([cx-7, cy_c-7, cx+7, cy_c+7], fill=GOLD)

        words = card_name.split()
        if len(words) <= 2:
            draw.text((cx, 487), card_name, font=f_title, fill=PALE, anchor='mm')
        else:
            mid = (len(words) + 1) // 2
            draw.text((cx, 472), ' '.join(words[:mid]),  font=f_title, fill=PALE, anchor='mm')
            draw.text((cx, 503), ' '.join(words[mid:]), font=f_title, fill=PALE, anchor='mm')
        draw.text((cx, 536), "· Major Arcana ·", font=f_label, fill=MID, anchor='mm')

    # ---- MINOR ARCANA ----
    else:
        parts = card_name.split(" of ")
        rank_word, suit = (parts[0], parts[1]) if len(parts) == 2 else ("", "")
        rank_num = _RANK_NUM.get(rank_word, 1)
        sc = _SUIT_COLOR.get(suit, GOLD)

        draw.text((cx, 90), _RANK_LABEL.get(rank_num, ""), font=f_rank, fill=sc, anchor='mm')

        cy_c = 280

        if rank_num >= 11:
            # Court card: concentric diamonds
            r = 72
            draw.polygon([(cx, cy_c-r),(cx+r,cy_c),(cx,cy_c+r),(cx-r,cy_c)],
                         outline=sc, fill=None)
            draw.polygon([(cx, cy_c-r+18),(cx+r-18,cy_c),(cx,cy_c+r-18),(cx-r+18,cy_c)],
                         outline=VIO, fill=None)
            _draw_pip(draw, cx, cy_c, suit, size=26, color=sc)
        else:
            layout = _PIP_LAYOUTS.get(rank_num, [(0, 0)])
            for dx, dy in layout:
                _draw_pip(draw, cx + dx, cy_c + dy, suit, size=20, color=sc)

        draw.text((cx, 472), _RANK_NAME.get(rank_num, rank_word), font=f_title, fill=PALE, anchor='mm')
        draw.text((cx, 503), f"of {suit}", font=f_title, fill=PALE, anchor='mm')
        draw.text((cx, 536), "· Minor Arcana ·", font=f_label, fill=MID, anchor='mm')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


# -----------------------------------------
# CUSTOM CSS
# -----------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Raleway:ital,wght@0,300;0,400;0,500;1,300&display=swap');

[data-testid="stAppViewContainer"] { background-color: #0E0C1A; }
[data-testid="stHeader"]           { background-color: #0E0C1A; }
[data-testid="stSidebar"]          { background-color: #0E0C1A; }

[data-testid="block-container"] {
    padding-top: 3rem;
    max-width: 720px;
    margin: 0 auto;
    text-align: center;
}

h1 {
    font-family: 'Cinzel', serif !important;
    color: #F0EAD6 !important;
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-align: center !important;
    margin-bottom: 0.2rem !important;
}

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

[data-testid="stTextInput"] input {
    background-color: #1A1628 !important;
    border: 1px solid #3A3258 !important;
    border-radius: 10px !important;
    color: #F0EAD6 !important;
    font-family: 'Raleway', sans-serif !important;
    font-size: 1rem !important;
    text-align: center !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #5C5470 !important;
    font-style: italic;
}
[data-testid="stTextInput"] input:focus {
    border-color: #7C5CBF !important;
    box-shadow: 0 0 0 2px rgba(124, 92, 191, 0.25) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div:focus-within {
    border-color: #7C5CBF !important;
    box-shadow: none !important;
}

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
    transition: background-color 0.2s ease;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #7045AA !important;
    border-color: #9B78D4 !important;
}

[data-testid="stAlert"] {
    background-color: #251E38 !important;
    border: 1px solid #7C5CBF !important;
    color: #F0EAD6 !important;
    border-radius: 8px !important;
    font-family: 'Raleway', sans-serif !important;
}

[data-testid="stSpinner"] p {
    color: #9B84B8 !important;
    font-family: 'Raleway', sans-serif !important;
}

/* Card image: no extra border since PIL already draws one */
[data-testid="stImage"] img {
    border-radius: 14px !important;
    border: none !important;
}

/* Padding above and below the reading result */
.reading-wrapper {
    padding-top: 2.5rem;
    padding-bottom: 2.5rem;
}

.reading-card {
    background-color: #1A1628;
    border: 1px solid #3A3258;
    border-radius: 14px;
    padding: 1.8rem 2rem;
    text-align: left;
    height: 100%;
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
    return card, CARD_MEANINGS[card]


def generate_with_openai(question, card, answer):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    user_prompt = f"Question: {question}\nCard: {card}\nPredetermined Answer: {answer}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
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


def render_reading(card_name, answer, reading):
    st.markdown('<div class="reading-wrapper">', unsafe_allow_html=True)
    col_img, col_text = st.columns([1, 1.4], gap="large")

    with col_img:
        card_img = make_card_image(card_name)
        st.image(card_img, use_container_width=True)

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
    st.markdown('</div>', unsafe_allow_html=True)


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
    st.markdown(
        '<p class="tarot-subtitle">The cards are listening. Ask what your heart seeks.</p>',
        unsafe_allow_html=True,
    )

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

            with st.spinner("Consulting the cards..."):
                try:
                    raw = generate_reading(question.strip(), card, answer)
                    card_name, parsed_answer, reading = parse_reading(raw)
                    if not card_name:    card_name    = card
                    if not parsed_answer: parsed_answer = answer
                    if not reading:      reading      = raw
                except Exception:
                    card_name     = card
                    parsed_answer = answer
                    reading       = (
                        f"The card speaks clearly. "
                        f"Its energy points firmly toward {answer.lower()}."
                    )

            st.session_state.result = {
                "card_name":    card_name,
                "answer":       parsed_answer,
                "reading":      reading,
            }
            st.session_state.has_drawn = True

    if st.session_state.result:
        r = st.session_state.result
        render_reading(r["card_name"], r["answer"], r["reading"])


if __name__ == "__main__":
    main()
