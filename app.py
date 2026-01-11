import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
import time
from datetime import datetime

# --- SECURE CONFIGURATION ---
# This line pulls the key from the 'Secrets' tab you set up in Streamlit Cloud
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
except KeyError:
    st.error("API Key not found. Please add 'GEMINI_API_KEY' to your Streamlit Secrets.")
    st.stop()

DB_FILE = "submissions_history.csv"
MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.0-flash"]

if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation' (5-7 minutes).

FOCUS ON:
1. Physical Details: Creator, materials, date, and method of creation.
2. Aesthetic Details: Harmony/melody, texture, color, etc.
3. Personal Experience: Connection between reaction and physical traits.
4. Delivery: Articulation, volume, rate, and transitions.

TONE: Qualitative, encouraging, and descriptive. No grades.
"""

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Practice", "Teacher Dashboard"])

if page == "Student Practice":
    st.title("🎙️ Aesthetics Speech Lab")
    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj_name = st.text_input("Aesthetic Object")
        audio_file = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Submit")

    if submitted and audio_file and name:
        with st.spinner("Analyzing presentation..."):
            ext = audio_file.name.split('.')[-1].lower()
            temp_path = f"temp_upload.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio_file.getbuffer())
            
            success = False
            for model_name in MODELS_TO_TRY:
                try:
                    uploaded_media = client.files.upload(
                        file=temp_path, 
                        config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"}
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                        contents=[uploaded_media, "Evaluate this presentation."]
                    )
                    st.subheader(f"Feedback ({model_name})")
                    st.markdown(response.text)
                    
                    new_entry = pd.DataFrame([[datetime.now(), name, obj_name, response.text]], 
                                            columns=["Timestamp", "Student", "Object", "Feedback"])
                    new_entry.to_csv(DB_FILE, mode='a', header=False, index=False)
                    success = True
                    break
                except Exception as e:
                    st.warning(f"Note: {model_name} is currently busy. Trying fallback...")
                    time.sleep(1)
            
            if not success:
                st.error("All models are currently exhausted. Please try again in 1 minute.")
            if os.path.exists(temp_path):
                os.remove(temp_path)

elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Password", type="password")
    if pw == "UMWAesthetics":
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            st.dataframe(df[["Timestamp", "Student", "Object"]], use_container_width=True)
            selected = st.selectbox("Review Student:", df["Student"].unique())
            st.markdown(df[df["Student"] == selected]["Feedback"].values[-1])
