import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime

# --- CONFIGURATION ---
GEMINI_API_KEY = "AIzaSyBw9yb6KklUo9KVZ44_17r4LhQjj5DNulk"
client = genai.Client(api_key=GEMINI_API_KEY)
DB_FILE = "submissions_history.csv"

# Initialize local CSV database
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

# Assignment Rubric from your document
SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course. 
Evaluate the 'Aesthetic Object Experience Presentation'.

CRITERIA:
1. Physical Details: Name, creator, object type, materials, date, and method of creation.
2. Aesthetic Details: Specific traits like harmony/melody (music) or texture/color (painting).
3. Experience: Why they chose it and how their reaction connects to physical traits.
4. Audience Connection: Why the audience should care and use of an aid.
5. Delivery: Articulation, volume, rate, and transitions.

TONE: Descriptive and qualitative. Do not assign grades. Focus on the student's observation of the world.
"""

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Practice", "Teacher Dashboard"])

# --- PAGE 1: STUDENT PRACTICE ---
if page == "Student Practice":
    st.title("🎙️ Aesthetics Speech Lab")
    st.info("Upload your 5-7 minute presentation for qualitative feedback.")

    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj_name = st.text_input("Aesthetic Object (e.g. 'Kind of Blue')")
        audio_file = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Submit for Analysis")

    if submitted and audio_file and name:
        with st.spinner("Gemini is listening to your presentation..."):
            # Step 1: Handle File & MIME types
            ext = audio_file.name.split('.')[-1].lower()
            mime_types = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4"}
            current_mime = mime_types.get(ext, "audio/mpeg")
            
            # Step 2: Save temporary file for upload
            temp_path = f"temp_upload.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio_file.getbuffer())
            
            try:
                # Step 3: Upload to Gemini Files API
                uploaded_media = client.files.upload(
                    file=temp_path,
                    config={'mime_type': current_mime}
                )
                
                # Step 4: Generate Multimodal Feedback
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    contents=[uploaded_media, "Evaluate my presentation's observations and delivery."]
                )
                
                # Step 5: Display & Store Results
                st.subheader("Professor Gemini's Feedback")
                st.markdown(response.text)
                
                new_entry = pd.DataFrame([[datetime.now(), name, obj_name, response.text]], 
                                        columns=["Timestamp", "Student", "Object", "Feedback"])
                new_entry.to_csv(DB_FILE, mode='a', header=False, index=False)
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

# --- PAGE 2: TEACHER DASHBOARD ---
elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    password = st.sidebar.text_input("Enter Dashboard Password", type="password")
    
    if password == "UMWAesthetics": # Replace with your preferred password
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.write("Current Submissions:")
                st.dataframe(df[["Timestamp", "Student", "Object"]], use_container_width=True)
                
                selected = st.selectbox("View full feedback for:", df["Student"].unique())
                feedback_text = df[df["Student"] == selected]["Feedback"].values[-1]
                st.markdown(f"### Feedback for {selected}\n{feedback_text}")
                
                # Download button for records
                st.download_button("Download CSV Records", df.to_csv(index=False), "class_history.csv", "text/csv")
            else:
                st.warning("No student submissions yet.")
    else:
        st.warning("Please enter the correct password in the sidebar to view student data.")