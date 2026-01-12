import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime

# --- 1. ACCESS CONTROL ---
ACCESS_CODE = "Aesthetics2024" 
TEACHER_PASSWORD = "UMWAesthetics"

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

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
            st.error("Incorrect code.")
    st.stop()

# --- 2. CONNECTIONS & SECRETS ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Initialize Google Sheets Connection
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.info("Check your Streamlit Secrets box for typos or missing quotes.")
    st.stop()

MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.0-flash"]
SYSTEM_PROMPT = "You are a Teaching Assistant for Dr. Reno's Aesthetics course..."

# --- 3. NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Practice", "Teacher Dashboard"])

# --- PAGE 1: STUDENT PRACTICE ---
if page == "Student Practice":
    st.title("🎙️ Student Practice Portal")
    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj_name = st.text_input("Aesthetic Object")
        audio_file = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Submit for Analysis")

    if submitted and audio_file and name:
        with st.spinner("Analyzing..."):
            ext = audio_file.name.split('.')[-1].lower()
            temp_path = f"temp_upload.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio_file.getbuffer())
            
            for model_name in MODELS_TO_TRY:
                try:
                    uploaded_media = client.files.upload(
                        file=temp_path, 
                        config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"}
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[uploaded_media, "Evaluate this presentation."]
                    )
                    
                    # SAVE TO GOOGLE SHEETS
                    existing_data = conn.read()
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Student": name,
                        "Object": obj_name,
                        "Feedback": response.text
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success("Feedback Saved to Class Log.")
                    st.markdown(response.text)
                    break
                except Exception as e:
                    st.warning(f"Retrying with fallback model... ({e})")
            if os.path.exists(temp_path): os.remove(temp_path)

# --- PAGE 2: TEACHER DASHBOARD (FIXED) ---
elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Teacher Password", type="password")
    
    if pw == TEACHER_PASSWORD:
        df = conn.read()
        if df is not None and not df.empty:
            # Fixes the display width warning
            st.dataframe(df[["Timestamp", "Student", "Object"]], width=None)
            
            student_list = df["Student"].unique().tolist()
            selected = st.selectbox("Select a Student:", student_list)
            
            # SAFE ACCESS: Use .iloc to prevent the IndexError
            if selected:
                student_data = df[df["Student"] == selected]
                if not student_data.empty:
                    feedback = student_data["Feedback"].iloc[-1]
                    st.subheader(f"Feedback for {selected}")
                    st.markdown(feedback)
        else:
            st.info("No submissions yet.")
