import streamlit as st
import os
import tempfile
import asyncio
import edge_tts
from PyPDF2 import PdfReader
import docx
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="AI Podcast Generator", layout="wide")

VOICE_OPTIONS = {
    "British Male": "en-GB-RyanNeural",
    "British Female": "en-GB-SoniaNeural",
    "American Male": "en-US-GuyNeural",
    "American Female": "en-US-JennyNeural",
    "Nigerian Male": "en-NG-AbeoNeural",
    "Nigerian Female": "en-NG-EzinneNeural"
}

OUTRO_MESSAGE = (
    "\n\n Thank you for listening! "
    "Remember to like, share, and subscribe for more exciting content like this. "
    "See you next time!"
)

# ---------------------- HELPERS ----------------------
def summarize_text_local(text, max_words=300):
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")

def extract_text_from_pdf(uploaded_file):
    pdf = PdfReader(uploaded_file)
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(uploaded_file):
    doc = docx.Document(uploaded_file)
    return " ".join([para.text for para in doc.paragraphs])

def extract_text_from_url(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    # Improved text extraction to grab more relevant content
    text_parts = [tag.get_text() for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])]
    return " ".join(text_parts)

def extract_text_from_youtube(url):
    """Extract transcript text from YouTube video if available."""
    try:
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        else:
            raise ValueError("Invalid YouTube URL")

        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript])
        return text
    except Exception as e:
        return f"⚠️ Could not fetch transcript: {e}"

async def text_to_speech_edge(text, voice, format="mp3"):
    fd, path = tempfile.mkstemp(suffix=f".{format}")
    os.close(fd)
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(path)
    return path

def generate_summary(text, use_openai=False, api_key=None):
    if use_openai and api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert podcast scriptwriter. Summarize the user's content clearly, engagingly, and naturally for a 3-5 minute spoken podcast segment."},
                    {"role": "user", "content": text}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"OpenAI API Error: {e}. Falling back to local summarization.")
            return summarize_text_local(text)
    else:
        return summarize_text_local(text)

# ---------------------- STREAMLIT APP ----------------------
st.title("🎙️ AI Podcast & Narration Generator")
st.write("Turn your scripts, PDFs, Word docs, websites, or YouTube videos into **engaging podcasts** with natural human-like voices.")

st.sidebar.header("⚙️ Settings")
voice_choice = st.sidebar.selectbox("Choose Voice", list(VOICE_OPTIONS.keys()))
output_format = st.sidebar.selectbox("Output Format", ["mp3", "wav", "mp4"])
use_openai = st.sidebar.checkbox("Use OpenAI API for Summarization?")
api_key = st.sidebar.text_input("Enter OpenAI API Key (optional)", type="password")

# ---------------------- INPUT SOURCES ----------------------
st.subheader("📥 Upload or Enter Content")

# --- MODIFIED RADIO OPTIONS ---
source_options = [
    "Final Script (Ready to Voice)", # NEW: Ready-to-voice script
    "Content for Summarization",      # Replaces "Text"
    "PDF",
    "Word",
    "URL",
    "YouTube",
    "Record Voice"
]
source_type = st.radio("Choose input type:", source_options)

input_text = ""
user_voice = None
needs_summary = True # Flag to control summarization

# --- MODIFIED INPUT HANDLING ---
if source_type == "Final Script (Ready to Voice)":
    input_text = st.text_area(
        "Paste your **finalized podcast script** here (will be voiced directly):",
        height=300,
        key="final_script_area"
    )
    needs_summary = False # Skip summarization

elif source_type == "Content for Summarization":
    input_text = st.text_area(
        "Enter content to be summarized:",
        height=200,
        key="long_text_area"
    )

elif source_type == "PDF":
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file:
        input_text = extract_text_from_pdf(uploaded_file)

elif source_type == "Word":
    uploaded_file = st.file_uploader("Upload Word File", type=["docx"])
    if uploaded_file:
        input_text = extract_text_from_docx(uploaded_file)

elif source_type == "URL":
    url = st.text_input("Enter a webpage URL:")
    if url:
        try:
            input_text = extract_text_from_url(url)
        except Exception:
            st.error("⚠️ Failed to fetch content from URL.")

elif source_type == "YouTube":
    yt_url = st.text_input("Enter YouTube Video URL:")
    if yt_url:
        input_text = extract_text_from_youtube(yt_url)

elif source_type == "Record Voice":
    st.info("🎤 You can record your own voice (feature placeholder).")
    user_voice = st.file_uploader("Upload your recorded voice", type=["mp3", "wav"])

# ---------------------- PROCESS ----------------------
if st.button("🚀 Generate Podcast"):
    if not input_text and not user_voice:
        st.error("⚠️ Please provide some input first!")
    else:
        if user_voice:
            st.success("✅ Using your uploaded voice file.")
            st.audio(user_voice)
        else:
            final_script = input_text

            # --- CONDITIONAL SUMMARIZATION ---
            if not input_text:
                st.error("⚠️ Input content is empty. Cannot generate script.")
                st.stop()

            if needs_summary:
                with st.spinner("Summarizing input..."):
                    final_script = generate_summary(input_text, use_openai, api_key)
                st.info("✅ Summarization complete.")
            else:
                 st.info("✅ Summarization skipped. Using the script as-is.")
            # ----------------------------------------

            final_script += OUTRO_MESSAGE  # append outro

            st.subheader("📝 Final Podcast Script")
            st.write(final_script)

            with st.spinner("🎧 Generating audio..."):
                # Use the new variable 'final_script'
                tts_path = asyncio.run(text_to_speech_edge(final_script, VOICE_OPTIONS[voice_choice], output_format))

            st.success("✅ Audio Generated!")
            st.audio(tts_path, format=f"audio/{output_format}")

            with open(tts_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Audio",
                    f,
                    file_name=f"podcast.{output_format}",
                    mime=f"audio/{output_format}"
                )

# ---------------------- ABOUT ----------------------
st.sidebar.markdown("---")
st.sidebar.subheader("👤 About the Developer")
st.sidebar.markdown("""
**Anthony Onoja, Ph.D.**
University of Surrey, United Kingdom

📧 Email: donmaston09@gmail.com
📺 YouTube: [@tonyonoja7880](https://www.youtube.com/@tonyonoja7880)
""")

st.sidebar.subheader("💡 About the App")
st.sidebar.markdown("""
This app helps **researchers, students, and professionals** turn written content into engaging podcasts.

It tackles:
- Information overload (summarizes PDFs/websites/YouTube into short scripts)
- Accessibility (listen instead of read)
- Localization (different voices & accents)
- Flexibility (text, docs, links, or personal voice uploads)
""")
