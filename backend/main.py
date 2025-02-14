import os
import requests
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    video_url: str

# Update this path to your FFmpeg installation directory
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"  # Adjust this path

# Step 1: Download audio from YouTube
def download_audio(youtube_url):
    output_path = "audio.mp3"
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
        "ffmpeg_location": FFMPEG_PATH,  # Specify FFmpeg location
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download audio: {str(e)}"
        )
    
    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=500,
            detail="Failed to create audio file"
        )
    
    return output_path

# Step 2: Upload audio to AssemblyAI for transcription
def transcribe_audio(audio_path):
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    
    # Upload audio file
    with open(audio_path, "rb") as f:
        response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, files={"file": f})
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to upload audio")
    
    audio_url = response.json()["upload_url"]

    # Start transcription
    json_data = {"audio_url": audio_url}
    response = requests.post("https://api.assemblyai.com/v2/transcript", json=json_data, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to start transcription")

    transcript_id = response.json()["id"]

    # Poll for transcription result
    while True:
        response = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
        status = response.json()["status"]
        if status == "completed":
            return response.json()["text"]
        elif status == "failed":
            raise HTTPException(status_code=500, detail="Transcription failed")

# Step 3: Generate quiz questions using Gemini API
def generate_quiz(transcript):
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
    prompt = f"Generate a quiz with 5 multiple-choice questions based on the following text:\n\n{transcript}"
    
    response = requests.post("https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateText", 
                             json={"prompt": prompt, "max_tokens": 200}, 
                             headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to generate quiz")
    
    return response.json().get("choices", [{}])[0].get("text", "").strip()

def parse_quiz_questions(quiz_text):
    # This is a simple parser - you might need to adjust based on Gemini's output format
    questions = []
    current_lines = []
    
    for line in quiz_text.split('\n'):
        if line.strip():
            current_lines.append(line)
        elif current_lines:
            question = ' '.join(current_lines)
            if 'Answer:' in question:
                q_part, a_part = question.split('Answer:', 1)
                questions.append({
                    "question": q_part.strip(),
                    "answer": a_part.strip()
                })
            current_lines = []
    
    return questions

# FastAPI endpoint to generate a quiz from a YouTube video
@app.post("/transcribe")
async def transcribe_video(request: VideoRequest):
    try:
        audio_path = download_audio(request.video_url)
        transcript = transcribe_audio(audio_path)
        quiz_questions = generate_quiz(transcript)
        
        # Clean up the audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return {
            "status": "success",
            "transcript": transcript,
            "quiz": parse_quiz_questions(quiz_questions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
