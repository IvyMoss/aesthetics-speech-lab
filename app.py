import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime

# --- CONFIGURATION ---
# To keep things simple, paste your new Gemini API key here.
# (Or put it in Streamlit Secrets as GEMINI_API_KEY)
API_KEY = st.secrets.get("GEMINI_API_KEY", "PASTE_YOUR_NEW_KEY_HERE")
client = genai.Client(api_key=API_KEY)

DB_FILE = "class_records.csv"
TEACHER_PASSWORD = "UMWAesthetics" 

# Initialize the local database file if it doesn't exist
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

# AI Prompt based on your AestheticsObjectPresentation.docx
SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation' (5-7 minutes).

RUBRIC REQUIREMENTS:
1. Physical Details: Name, creator, type of object, materials, date, and method of creation.
2. Aesthetic Details: Specific traits (e.g., harmony/melody for music, color/texture for painting).
3. Personal Experience: Why they chose it and how their reaction connects to the object's physical/aesthetic traits.
4. Audience Connection: Why should the audience care? Is there a clear way for them to connect?
5. Delivery: Articulation, pronunciation, volume, and rate.
6. Organization: Clear transitions and a stated purpose.

TONE: Qualitative and encouraging. Focus on descriptive observation. Do not assign a grade. Give at least one criticism and one thing they did well. 
"""

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

# --- NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Go to:", ["Student Upload", "Teacher Dashboard"])

# --- PAGE 1: STUDENT UPLOAD ---
if page == "Student Upload":
    st.title("🎙️ Aesthetics Speech Lab")
    st.markdown("Upload your 5-7 minute presentation for qualitative feedback.")

    with st.form("upload_form"):
        name = st.text_input("Full Name")
        obj_name = st.text_input("Aesthetic Object")
        audio = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
        submit = st.form_submit_button("Get Feedback")

    if submit and audio and name:
        with st.spinner("Analyzing your presentation..."):
            # Save audio temporarily
            ext = audio.name.split('.')[-1].lower()
            temp_path = f"temp_speech.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio.getbuffer())
            
            try:
                # Upload to Gemini (Using 1.5-flash for better stability)
                uploaded_file = client.files.upload(
                    file=temp_path,
                    config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"}
                )
                
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    contents=[uploaded_file, "Evaluate this student presentation based on our rubric."]
                )
                
                # Show feedback on screen
                st.subheader("Professor Gemini's Feedback")
                st.markdown(response.text)
                
                # Save to local CSV
                new_data = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), name, obj_name, response.text]], 
                                        columns=["Timestamp", "Student", "Object", "Feedback"])
                new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.success("Feedback saved to teacher dashboard.")

            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

# --- PAGE 2: TEACHER DASHBOARD ---
elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Password", type="password")
    
    if pw == TEACHER_PASSWORD:
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.write("Recent Submissions:")
                st.dataframe(df[["Timestamp", "Student", "Object"]], width=None)
                
                # Safely select student
                selected = st.selectbox("View full feedback for:", df["Student"].unique())
                if selected:
                    feedback = df[df["Student"] == selected]["Feedback"].iloc[-1]
                    st.markdown(f"### Feedback for {selected}")
                    st.markdown(feedback)
                
                st.markdown("---")
                st.download_button("💾 Download All Records (Save to PC)", df.to_csv(index=False), "aesthetics_records.csv")
            else:
                st.info("No submissions found yet.")
    else:
        st.warning("Enter teacher password to view records.")
