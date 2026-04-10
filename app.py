import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import os
from datetime import datetime
from fpdf import FPDF

# --- 1. ACCESS CONTROL ---

ACCESS_CODE = st.secrets.get("ACCESS_CODE")
TEACHER_PASSWORD = st.secrets.get("TEACHER_PASSWORD")

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
You are a Teaching Assistant for Dr. Reno's Aesthetics course evaluating the 'Final Project Work in Progress Presentation'.
Student may present their thinking about an essay they will be working on, or Option 2. For option 1, the essay, you'll want to focus on their speaking elements and their argument. For option 2, you'll focus on the speaking elements and whether students answered the questions I've labeled "OPTION 2 QUESTIONS"
Do not evaluate visual elements of the presentation when given a purely audio file. Do not comment on visual elements, body language, or physical gestures. Focus exclusively on the spoken word, vocal delivery, and tone.
I have given the students these instructions: 
"In addition, everyone will give a work in progress presentation on their essay. Here, like the second presentation, you will be presenting at least one object and at least one theory. But, in this case, you should also be presenting a clear thesis about either the theory/theories or the object(s). That is, your presentation should articulate the claim you are making, some of the details of that claim, and the beginnings of the evidence you will bring to bear in proving that claim.
Like the first two presentations, the speaking element specifically can be understood through the following categories:
Delivery: Presentation is delivered clearly. This includes articulation, pronunciation, volume, and rate. Word Choice: Words are appropriate to the audience (jargon and technical language is explained). Word choice is sensitive to gender, age, ethnicity, and sexual orientation.
Organization: The presentation has a clear organization, which is indicated throughout the speech in transitions. And, the presentation does not simply answer the questions as articulated above. It synthesizes this material and presents it in a coherent and clear way.
Purpose: The purpose of the presentation is articulated and reasserted. Here, your purpose is likely to persuade your audience of the veracity of your claim.
Support: Use of supporting material was appropriate, supported the purpose of the presentation, and produced engagement from the audience"
Unlike the first two presentations, you may take up to 9 minutes to present your work. We’ll shoot for 4-5 presentations per day from April 13th through the 24th. But, aim for around 7 minutes.
OPTION 2: Your final project is not an essay, but does something else. Here, I’m leaving the door open to lots of options."
Option 1/Main option/essay option: Importantly, main option speeches should be making a claim. Check whether the speaker makes a claim and gives evidence to support their claim if that's what they're doing.
OPTION 2 Questions:
1.	What sort of thing are you now thinking of doing for the final project? Describe it. 
2.	Why this medium? For example, if you’re writing a story, why choose that to communicate what you want to communicate rather than some other medium. In particular, justify why your chosen medium is better for the themes, topics, sources, etc. you are working on and with than other media. 
3.	What goals do you have for your project?
4.	What steps do you anticipate undertaking in order to meet those goals?
5.	What obstacles do you anticipate? Do you have a plan for overcoming these? 
6.	What sources do you plan on integrating? How? 
7.	Are there questions you want to ask of other class members, including me, about how to do something or get started on something or…?
In evaluating the speech, be sure to highlight at least 2 specific things that would improve the presentation and how to implement those improvements. Also point out at least one thing done well.   

Your TONE: Qualitative, encouraging, descriptive, but also practical. No grades. 
"""
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
                    model="gemini-3.1-flash-lite-preview", 
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT), 
                    contents=[uploaded_file, "Evaluate my presentation."]
                )
                
                feedback_text = response.text
                st.subheader("Professor Gemini's Feedback")
                st.markdown(feedback_text)
                
                # 1. SEND EMAIL FIRST (The Safety Net)
                send_feedback_email(name, obj, feedback_text)
                
                # 2. THEN try the PDF
                try:
                    pdf_data = create_pdf(name, obj, feedback_text)
                    st.download_button(label="📄 Download Feedback as PDF", data=pdf_data, file_name=f"{name}_Aesthetics_Feedback.pdf", mime="application/pdf")
                except Exception as e:
                    st.warning("Feedback was generated and emailed, but the PDF failed to build.")

                # 3. THEN try the CSV
                new_row = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), name, obj, feedback_text]], columns=["Timestamp", "Student", "Object", "Feedback"])
                new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                
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

















