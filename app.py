import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db
import requests
from PIL import Image
from io import BytesIO
import base64
import os
import json

from dotenv import load_dotenv
load_dotenv()
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")


# ------------------ API KEYS ------------------

# ------------------ FIREBASE CONFIG ------------------
if os.path.exists("mana-oori-matalu-firebase-adminsdk-fbsvc-8001155175.json"):
    cred = credentials.Certificate("mana-oori-matalu-firebase-adminsdk-fbsvc-8001155175.json")
else:
    st.error("Firebase JSON file not found. Place it in the same folder as app.py.")
    st.stop()

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://mana-oori-matalu-default-rtdb.firebaseio.com/"
    })

ref = db.reference("stories")

# ------------------ GEMINI CONFIG ------------------
genai.configure(api_key=GEMINI_API_KEY)

# ------------------ FUNCTIONS ------------------
def generate_story_card(story_text, language, image_file):
    # 1. Generate improved story text using Gemini 1.5 Flash
    prompt = f"Create a poetic and culturally rich story card text in {language}:\n{story_text}"
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    response = model.generate_content(prompt)
    card_text = response.text.strip()

    # 2. Generate AI background image with Stable Diffusion
    img_prompt = f"Artistic illustration for a folk story in {language}, vibrant and colorful."
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    img_resp = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers=headers,
        json={"inputs": img_prompt}
    )
    bg_img = Image.open(BytesIO(img_resp.content))

    # If user uploaded an image, overlay it
    if image_file:
        user_img = Image.open(image_file).resize((512, 512))
        bg_img.paste(user_img, (0, 0), user_img.convert("RGBA"))

    final_path = "story_card.png"
    bg_img.save(final_path)
    return final_path, card_text

def save_to_firebase(language, story_text, card_text, image_path):
    with open(image_path, "rb") as img_file:
        b64_img = base64.b64encode(img_file.read()).decode("utf-8")
    ref.push({
        "language": language,
        "story_text": story_text,
        "card_text": card_text,
        "image": b64_img
    })

def fetch_gallery():
    data = ref.get()
    gallery = []
    if data:
        for item in data.values():
            img = Image.open(BytesIO(base64.b64decode(item["image"])))
            gallery.append((img, f"{item['language']}: {item['card_text']}"))
    return gallery

# ------------------ STREAMLIT UI ------------------
st.title("🌾 Mana Oori Matalu")
st.markdown("### Share your village’s stories, proverbs, and cultural gems in your language!")

language = st.selectbox("Select Language", ["Telugu", "Hindi", "Tamil", "Kannada", "Malayalam", "Marathi"])
story_text = st.text_area("Write your story or proverb (≤300 words)")
image_file = st.file_uploader("Optional: Upload an image", type=["png", "jpg", "jpeg"])

if st.button("Generate Story Card"):
    if story_text.strip():
        with st.spinner("Generating your story card..."):
            card_path, card_text = generate_story_card(story_text, language, image_file)
            save_to_firebase(language, story_text, card_text, card_path)
            st.success("Story card generated successfully!")
            st.image(card_path, caption="Your Story Card")
            st.text_area("Generated Story Text", card_text)
    else:
        st.error("Please enter a story.")

st.markdown("## 🌍 Community Gallery")
gallery = fetch_gallery()
if gallery:
    for img, caption in gallery:
        st.image(img, caption=caption)
else:
    st.info("No stories yet. Be the first to share!")
