import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime

# --- CONFIGURATION ---
# Use the Secret you set in Streamlit, or paste a fresh key below.
API_KEY = st.secrets.get("GEMINI_API_KEY", "PASTE_YOUR_NEW_KEY_HERE")
client = genai.Client(api_key=API_KEY)

DB_FILE = "aesthetics_log.csv"
TEACHER_PASSWORD = "UMWAesthetics" 

# Ensure the database file exists
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

# Rubric pulled from your AestheticsObjectPresentation.docx
SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation' (5-7 minutes).

REQUIREMENTS TO CHECK:
1. Physical details (Creator, materials, date, method).
2. Aesthetic details (Harmony, texture, color, etc.).
3. Personal experience and connection to the object.
4. Audience connection and use of an aid.
5. Delivery (Articulation, volume, rate).
6. Organization (Transitions and clear purpose).

TONE: Qualitative, supportive, and descriptive. Do not give a grade.
"""

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Upload", "Teacher Dashboard"])

# --- PAGE 1: STUDENT UPLOAD ---
if page == "Student Upload":
    st.title("🎙️ Aesthetics Speech Lab")
    st.info("Upload your 5-7 minute presentation for qualitative feedback.")

    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj = st.text_input("Aesthetic Object Name")
        audio = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Analyze Presentation")

    if submitted and audio and name:
        with st.spinner("Gemini is listening to your speech..."):
            ext = audio.name.split('.')[-1].lower()
            temp_path = f"temp_audio.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio.getbuffer())
            
            try:
                # Upload to Gemini (Native Multimodal)
                uploaded_file = client.files.upload(
                    file=temp_path,
                    config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"}
                )
                
                # Using 2.0-flash as the primary model
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    contents=[uploaded_file, "Please evaluate my presentation observations and delivery."]
                )
                
                st.subheader("Professor Gemini's Feedback")
                st.markdown(response.text)
                
                # Store in Local CSV
                new_row = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), name, obj, response.text]], 
                                        columns=["Timestamp", "Student", "Object", "Feedback"])
                new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.success("Success! Your feedback has been logged for Dr. Reno.")

            except Exception as e:
                st.error(f"Analysis Error: {e}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

# --- PAGE 2: TEACHER DASHBOARD ---
elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Dashboard Password", type="password")
    
    if pw == TEACHER_PASSWORD:
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.write("Recent Activity:")
                st.dataframe(df[["Timestamp", "Student", "Object"]], width=None)
                
                selected_student = st.selectbox("Select a Student to view feedback:", df["Student"].unique())
                if selected_student:
                    # Get the most recent feedback for this specific student
                    feedback = df[df["Student"] == selected_student]["Feedback"].iloc[-1]
                    st.markdown(f"### Full Critique for {selected_student}")
                    st.info(feedback)
                
                st.divider()
                st.download_button("💾 Download Permanent CSV", df.to_csv(index=False), "aesthetics_records.csv")
            else:
                st.warning("No student records found yet.")
    else:
        st.warning("Please enter the teacher password to access student data.")
