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

# Ensure CSV exists with correct columns
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Timestamp", "Student", "Object", "Feedback"]).to_csv(DB_FILE, index=False)

SYSTEM_PROMPT = """
You are a Teaching Assistant for Dr. Reno's Aesthetics course evaluating the 'Aesthetic Object Experience Presentation'.
In evaluating the speech, be sure to highlight at least 2 specific things that would improve the presentation and how to implement those improvements.  
Give an evaluation of the presentation's account of Physical details, Aesthetic details, Personal experience. In addition evaluate the speech's Audience connection and Delivery.
Your TONE: Qualitative, encouraging, descriptive, but also practical. No grades. 
"""

# PDF Generation Function (Fixed for Encoding Errors)
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
    
    # FPDF1 doesn't like UTF-8/Special characters from AI. We encode/decode to strip them.
    clean_feedback = feedback.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_feedback)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. NAVIGATION ---
st.sidebar.title("Aesthetics Lab")
page = st.sidebar.radio("Navigation", ["Student Upload", "Teacher Dashboard"])

import smtplib
from email.mime.text import MIMEText




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
            
# Find the part where 'feedback_text = response.text' is called:

            try:
                uploaded_file = client.files.upload(file=temp_path, config={'mime_type': f"audio/{'mpeg' if ext == 'mp3' else ext}"})
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT), 
                    contents=[uploaded_file, "Evaluate my presentation."]
                )
                
                feedback_text = response.text
                st.subheader("Professor Gemini's Feedback")
                st.markdown(feedback_text)
                
                # --- TRIGGER EMAIL HERE ---
                send_feedback_email(name, obj, feedback_text)
                # --------------------------
                
                # Continue with PDF and CSV logging...

                
                # PDF Download
                pdf_data = create_pdf(name, obj, feedback_text)
                st.download_button(label="📄 Download Feedback as PDF", data=pdf_data, file_name=f"{name}_Aesthetics_Feedback.pdf", mime="application/pdf")
                
                # Log to CSV
                new_row = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), name, obj, feedback_text]], columns=["Timestamp", "Student", "Object", "Feedback"])
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
                st.dataframe(df[["Timestamp", "Student", "Object"]], use_container_width=True)
                
                # Added safety check for unique students
                student_list = df["Student"].unique()
                selected_student = st.selectbox("Review Student:", student_list)
                
                if selected_student:
                    # Get the most recent feedback for that student
                    student_data = df[df["Student"] == selected_student]
                    fb = student_data["Feedback"].iloc[-1]
                    st.info(f"**Latest Feedback for {selected_student}:**\n\n{fb}")
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("💾 Download All Records (CSV)", csv_data, "aesthetics_records.csv", "text/csv")
            else:
                st.warning("No student records found yet.")
    elif pw != "":
        st.error("Incorrect Teacher Password")

        # --- DEBUG: FILE CHECKER ---
with st.expander("🛠️ Server File System Check (Debug)"):
    files = os.listdir(".")
    st.write("Files currently on server:", files)
    
    if DB_FILE in files:
        file_size = os.path.getsize(DB_FILE)
        st.success(f"Found {DB_FILE}! Size: {file_size} bytes")
        
        # Emergency view of the raw file
        with open(DB_FILE, "r") as f:
            st.text_area("Raw CSV Content:", f.read(), height=200)
    else:
        st.error(f"Could not find {DB_FILE} in the current directory.")
# ---------------------------
# --- NEW: EMAIL FUNCTION ---
def send_feedback_email(student_name, object_name, feedback_text):
    try:
        # Pull credentials from Streamlit Secrets
        sender = st.secrets["EMAIL_SENDER"]
        receiver = st.secrets["EMAIL_RECEIVER"]
        password = st.secrets["EMAIL_PASSWORD"]

        msg = MIMEText(f"Student: {student_name}\nObject: {object_name}\n\nFeedback:\n{feedback_text}")
        msg['Subject'] = f"Aesthetics Lab: {student_name}"
        msg['From'] = sender
        msg['To'] = receiver

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email notification failed: {e}")
        return False
# --- DEBUG: TEST EMAIL BUTTON ---
st.sidebar.markdown("---")
if st.sidebar.button("🧪 Send Test Email"):
    st.sidebar.info("Attempting to send...")
    
    # Use the same logic as your main function
    success = send_feedback_email("Test Student", "Test Object", "This is a test message to verify the email connection.")
    
    if success:
        st.sidebar.success("Test Email Sent! Check your inbox (and Spam).")
    else:
        st.sidebar.error("Test Failed. Check the main screen for the error details.")











