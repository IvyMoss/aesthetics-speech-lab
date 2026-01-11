import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os

# API key provided
GEMINI_API_KEY = "AIzaSyBw9yb6KklUo9KVZ44_17r4LhQjj5DNulk"
client = genai.Client(api_key=GEMINI_API_KEY)

# System Instruction focused on Qualitative Observation
SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation' (5-7 minutes).

FOCUS AREAS:
1. Physical Inventory: Did they identify the creator, materials, and creation method?
2. Aesthetic Details: Did they describe specific traits (e.g., texture, melody, color)?
3. The Experience: How well did they connect their reaction to the object's physical traits?
4. Delivery: Note their pacing, articulation, and use of transitions.

Tone: Encouraging and descriptive. Avoid philosophical theory; focus on the student's ability to 'attend to the world'.
"""

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

st.title("🎙️ Aesthetics Speech Lab")
st.markdown("Use this tool to practice your **Aesthetic Object Presentation**. Gemini will provide qualitative feedback on your observations and delivery.")

# Form for Student Upload
with st.form("upload_form"):
    student_name = st.text_input("Student Name")
    object_desc = st.text_input("Object being presented")
    uploaded_file = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
    submit = st.form_submit_button("Analyze Speech")

if submit and uploaded_file and student_name:
    with st.spinner("Analyzing your presentation..."):
        # Temporary save for processing
        with open("temp_speech.mp3", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Multimodal Audio Upload
        audio_file = client.files.upload(file="temp_speech.mp3")
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            contents=["Provide qualitative feedback on this presentation.", audio_file]
        )
        
        st.subheader(f"Feedback for {student_name}")
        st.markdown(response.text)
        
        # Option for student to download their feedback as text
        st.download_button("Download Feedback as TXT", response.text, file_name=f"{student_name}_feedback.txt")