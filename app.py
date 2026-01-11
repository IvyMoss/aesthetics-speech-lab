import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime
import time

# --- 1. ACCESS CONTROL ---
ACCESS_CODE = "Aesthetics2024"  # Give this to your students
TEACHER_PASSWORD = "UMWAesthetics"

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

# Simple login session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 Aesthetics Lab Login")
    user_input = st.text_input("Enter the Class Access Code:", type="password")
    if st.button("Login"):
        if user_input == ACCESS_CODE:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect code. Please check your syllabus.")
    st.stop()

# --- 2. CONNECTIONS & SECRETS ---
try:
    # Gemini AI Setup
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Google Sheets Setup
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Configuration Error: Please ensure 'GEMINI_API_KEY' and '[connections.gsheets]' are set in Streamlit Secrets.")
    st.stop()

# Fallback models to handle "429 Resource Exhausted" errors
MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.0-flash"]

SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation' (5-7 minutes).
Focus on: Physical details (creator, material, date), Aesthetic details, Personal Experience, and Delivery.
TONE: Qualitative, encouraging, and descriptive. Do not assign grades.
"""

# --- 3. NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

page = st.sidebar.radio("Navigation", ["Student Practice", "Teacher Dashboard"])

# --- PAGE 1: STUDENT PRACTICE ---
if page == "Student Practice":
    st.title("🎙️ Student Practice Portal")
    st.info("Upload your speech to receive qualitative feedback on your observation and delivery.")

    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj_name = st.text_input("Aesthetic Object")
        audio_file = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Submit for Analysis")

    if submitted and audio_file and name:
        with st.spinner("Professor Gemini is listening..."):
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
                        contents=[uploaded_media, "Provide qualitative feedback on this presentation."]
                    )
                    
                    # --- SAVE TO GOOGLE SHEETS ---
                    # 1. Read existing data
                    existing_data = conn.read()
                    
                    # 2. Create new row
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Student": name,
                        "Object": obj_name,
                        "Feedback": response.text
                    }])
                    
                    # 3. Use pd.concat (replaces the deprecated .append)
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success("Analysis Complete! Your feedback has been saved to the class log.")
                    st.subheader(f"Feedback ({model_name})")
                    st.markdown(response.text)
                    success = True
                    break
                except Exception as e:
                    if "429" in str(e):
                        st.warning(f"Note: {model_name} is currently at capacity. Trying fallback...")
                        time.sleep(2)
                    else:
                        st.error(f"Error: {str(e)}")
            
            if not success:
                st.error("All AI models are currently exhausted. Please try again in a few minutes.")
            
            if os.path.exists(temp_path):
                os.remove(temp_path)

# --- PAGE 2: TEACHER DASHBOARD ---
elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Teacher Password", type="password")
    
    if pw == TEACHER_PASSWORD:
        # Re-fetch data from Google Sheets
        df = conn.read()
        
        if df is not None and not df.empty:
            st.write("Current Submissions:")
            # UPDATED: use width="stretch" to satisfy new Streamlit standards
            st.dataframe(df[["Timestamp", "Student", "Object"]], width="stretch")
            
            # Populate selection box
            student_list = df["Student"].unique().tolist()
            selected = st.selectbox("Select a Student to review full feedback:", student_list)
            
            # SAFE ACCESS: Check if selection exists to prevent IndexError
            if selected:
                student_data = df[df["Student"] == selected]
                if not student_data.empty:
                    feedback = student_data["Feedback"].iloc[-1]
                    st.markdown("---")
                    st.subheader(f"Feedback for {selected}")
                    st.markdown(feedback)
        else:
            st.info("The Google Sheet is currently empty. Submissions will appear here once students use the app.")
    else:
        st.warning("Please enter the teacher password in the sidebar to view student records.")
