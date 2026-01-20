import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime
from fpdf import FPDF

# --- 1. ACCESS CONTROL ---
ACCESS_CODE = "Aesthetics2026" 
TEACHER_PASSWORD = "UMWAesthetics"

st.set_page_config(page_title="Aesthetics Speech Lab", page_icon="🎙️")

# Session State for Authentication
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

# --- 2. CONFIGURATION ---
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
DB_FILE = "aesthetics_log.csv"

if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course evaluating the 'Aesthetic Object Experience Presentation'.
In evaluating the speech, be sure to highlight at least 2 specific things that would improve the presentation (you may spell out more areas if applicable) and how to implement those improvements.  
Focus on: Physical details, Aesthetic details, Personal experience, Audience connection, and Delivery (articulation, volume, rate).
TONE: Qualitative, encouraging, descriptive, but also practical and process oriented. No grades. 
"""

# PDF Generation Function
def create_pdf(name, obj, feedback):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Aesthetics Speech Lab Feedback", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Student: {name}", ln=True)
    pdf.cell(200, 10, txt=f"Object: {obj}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=feedback)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Upload", "Teacher Dashboard"])

if page == "Student Upload":
    st.title("🎙️ Student Practice Portal")
    with st.form("speech_form"):
        name = st.text_input("Full Name")
        obj = st.text_input("Aesthetic Object")
        audio = st.file_uploader("Upload Audio (MP3/WAV/M4A)", type=['mp3', 'wav', 'm4a'])
        submitted = st.form_submit_button("Analyze Presentation")

    if submitted and audio and name:
        with st.spinner("Analyzing..."):
            ext = audio.name.split('.')[-1].lower()
            temp_path = f"temp_audio.{ext}"
            with open(temp_path, "wb") as f:
                f.write(audio.getbuffer())
            
            try:
                uploaded_file = client.files.upload(file=temp_path, config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"})
                response = client.models.generate_content(model="gemini-2.0-flash", config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT), contents=[uploaded_file, "Evaluate my presentation."])
                
                st.subheader("Professor Gemini's Feedback")
                st.markdown(response.text)
                
                # PDF Download Button
                pdf_data = create_pdf(name, obj, response.text)
                st.download_button(label="📄 Download Feedback as PDF", data=pdf_data, file_name=f"{name}_Aesthetics_Feedback.pdf", mime="application/pdf")
                
                # Log to CSV
                new_row = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), name, obj, response.text]], columns=["Timestamp", "Student", "Object", "Feedback"])
                new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.success("Feedback logged successfully.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)

elif page == "Teacher Dashboard":
    st.title("👨‍🏫 Teacher Overview")
    pw = st.sidebar.text_input("Password", type="password")
    if pw == TEACHER_PASSWORD:
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.dataframe(df[["Timestamp", "Student", "Object"]], width=None)
                selected_student = st.selectbox("Review Student:", df["Student"].unique())
                if selected_student:
                    fb = df[df["Student"] == selected_student]["Feedback"].iloc[-1]
                    st.info(fb)
                st.download_button("💾 Download All Records (CSV)", df.to_csv(index=False), "aesthetics_records.csv")



