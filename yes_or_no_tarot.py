
import random
import streamlit as st
from openai import OpenAI
from google import genai

# -----------------------------------------
# TAROT DECK (78 CARDS)
# Fixed YES/NO meanings based on card index.
# This ensures each card always has the same answer.
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

# Alternate YES/NO so each card has a fixed meaning.
CARD_MEANINGS = {
    card: ("YES" if i % 2 == 0 else "NO")
    for i, card in enumerate(TAROT_DECK)
}

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


def draw_random_card():
    """Select one card uniformly at random from the full 78-card deck."""
    card = random.choice(TAROT_DECK)
    answer = CARD_MEANINGS[card]
    return card, answer


def generate_with_openai(question, card, answer):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    user_prompt = f"""
Question: {question}
Card: {card}
Predetermined Answer: {answer}
"""

    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
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

    user_prompt = f"""
Question: {question}
Card: {card}
Predetermined Answer: {answer}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=[SYSTEM_PROMPT, user_prompt]
    )

    return extract_gemini_text(response)


def generate_reading(question, card, answer):
    # Try OpenAI first; silently fall back to Gemini.
    try:
        return generate_with_openai(question, card, answer)
    except Exception:
        return generate_with_gemini(question, card, answer)


def main():
    st.set_page_config(
        page_title="Yes or No Tarot",
        page_icon="🔮",
        layout="centered"
    )

    st.header("🔮 Yes or No Tarot")
    st.subheader("Ask the cards. Receive a clear answer.")

    st.write(
        "Enter your question and draw one card from the full 78-card tarot deck. "
        "Each card carries a fixed YES or NO meaning."
    )

    question = st.text_input(
        "Your Yes-or-No Question",
        placeholder="Will I get the job?"
    )

    if st.button("✨ Draw a Card", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
            return

        card, answer = draw_random_card()

        with st.spinner("Consulting the cards..."):
            try:
                reading = generate_reading(question.strip(), card, answer)
            except Exception:
                # Guaranteed fallback if both APIs fail
                reading = (
                    f"Card: {card}\n"
                    f"Answer: {answer}\n"
                    f"Reading: The card speaks clearly. Its energy points firmly toward {answer.lower()}."
                )

        st.markdown("### 🃏 Your Reading")
        st.write(reading)

        st.caption(
            "Cards are selected randomly from all 78 tarot cards. "
            "OpenAI is used first, with automatic silent fallback to Gemini if needed."
        )


if __name__ == "__main__":
    main()
