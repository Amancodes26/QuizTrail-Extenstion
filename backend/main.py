import os
import time
import requests
import google.generativeai as genai
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, RegexMatchError, PytubeError
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import traceback
import shutil
import imageio_ffmpeg as ffmpeg
import assemblyai as aai

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Load API keys from .env file
load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

app = FastAPI()

# Update CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    video_url: str

def download_audio_pytube(youtube_url):
    """Attempt to download audio using PyTube"""
    try:
        logger.info(f"Starting PyTube download from: {youtube_url}")
        timestamp = int(time.time())
        output_path = f"audio_{timestamp}.mp4"
        
        yt = YouTube(youtube_url)
        yt.check_availability()
        logger.info(f"Video title: {yt.title}")
        
        streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        if not streams:
            raise Exception("No audio streams found")
        
        audio_stream = streams[0]
        logger.info(f"Selected audio stream: {audio_stream.abr}kbps")
        audio_stream.download(filename=output_path)
        
        if not os.path.exists(output_path):
            raise Exception("Failed to create audio file")
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise Exception("Downloaded file is empty")
            
        logger.info(f"PyTube download successful. File size: {file_size} bytes")
        return output_path
    except Exception as e:
        logger.error(f"PyTube error: {str(e)}")
        raise

def get_ffmpeg_path():
    """Get FFmpeg path using imageio_ffmpeg"""
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        logger.info(f"Found FFmpeg at: {ffmpeg_path}")
        return ffmpeg_path
    except Exception as e:
        logger.error(f"FFmpeg not found: {str(e)}")
        return None

# Update FFmpeg path using imageio_ffmpeg
FFMPEG_PATH = get_ffmpeg_path()

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
CHROME_VERSION = '120.0.0.0'

# Add constants for retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5
DOWNLOAD_TIMEOUT = 300  # 5 minutes

def download_audio_ytdlp(youtube_url):
    """Attempt to download audio using yt-dlp with retries"""
    timestamp = int(time.time())
    output_path = f"audio_{timestamp}.mp3"
    last_exception = None
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
        'quiet': False,
        'verbose': True,
        'http_headers': {
            'User-Agent': USER_AGENT,
            'Referer': 'https://www.youtube.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'socket_timeout': DOWNLOAD_TIMEOUT,
        'retries': 10,  # Internal yt-dlp retries
        'nocheckcertificate': True,
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Download attempt {attempt + 1}/{MAX_RETRIES} for: {youtube_url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                
                if not info:
                    raise Exception("Failed to extract video info")
                
                if not os.path.exists(output_path):
                    raise Exception(f"Output file not found: {output_path}")
                    
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    raise Exception("Downloaded file is empty")
                    
                logger.info(f"Download successful on attempt {attempt + 1}")
                logger.info(f"File size: {file_size} bytes")
                logger.info(f"Title: {info.get('title', 'Unknown')}")
                return output_path
                
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)  # Progressive delay
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            
            # Clean up failed download
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
    
    error_msg = f"Download failed after {MAX_RETRIES} attempts. Last error: {str(last_exception)}"
    logger.error(error_msg)
    raise Exception(error_msg)

def download_audio(youtube_url):
    """Main download function with fallback strategy"""
    errors = []
    
    # Try yt-dlp with retries first
    try:
        return download_audio_ytdlp(youtube_url)
    except Exception as e:
        errors.append(f"yt-dlp error: {str(e)}")
        logger.warning("yt-dlp failed, trying PyTube...")
        
        # Try PyTube as fallback
        try:
            return download_audio_pytube(youtube_url)
        except Exception as e:
            errors.append(f"PyTube error: {str(e)}")
            error_msg = "All download methods failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

# Update the transcribe_audio function
def transcribe_audio(audio_path):
    """Transcribe audio using AssemblyAI official package"""
    try:
        # Configure API key
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        
        # Initialize transcriber
        transcriber = aai.Transcriber()
        
        # Start transcription
        logger.info("Starting transcription...")
        transcript = transcriber.transcribe(audio_path)
        
        # Check status
        if transcript.status == aai.TranscriptStatus.error:
            error_msg = f"Transcription failed: {transcript.error}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
        if not transcript.text:
            raise HTTPException(
                status_code=500,
                detail="No transcription text received"
            )
            
        logger.info("Transcription completed successfully")
        return transcript.text
        
    except Exception as e:
        error_msg = f"Transcription error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Step 3: Generate quiz questions using Gemini API
def generate_quiz(transcript):
    try:
        prompt = f"""Generate a quiz with 5 multiple-choice questions based on this transcript. 
        Format each question as:
        Q1: [Question]
        A) [Option]
        B) [Option]
        C) [Option]
        D) [Option]
        Answer: [Correct letter]

        Transcript: {transcript}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

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

@app.get("/")
async def root():
    return {"message": "API is working!"}

# Add error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({
            "status": "error",
            "detail": str(exc.detail),
            "message": str(exc.detail)
        })
    )

# FastAPI endpoint to generate a quiz from a YouTube video
@app.post("/transcribe")
async def transcribe_video(request: VideoRequest):
    if not FFMPEG_PATH:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg not found. Please install FFmpeg first."
        )
    
    audio_path = None
    try:
        if not request.video_url:
            raise HTTPException(status_code=400, detail="No video URL provided")
            
        logger.info(f"Processing video URL: {request.video_url}")
        
        # Validate video URL
        if not request.video_url.startswith("https://www.youtube.com/watch?v="):
            raise HTTPException(
                status_code=400, 
                detail="Invalid YouTube URL format"
            )
        
        # Download audio with detailed error tracking
        try:
            audio_path = download_audio(request.video_url)
            logger.info(f"Audio downloaded successfully to: {audio_path}")
        except Exception as e:
            logger.error(f"Audio download failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio download failed: {str(e)}"
            )
        
        # Transcribe with error handling
        try:
            transcript = transcribe_audio(audio_path)
            logger.info("Transcription completed successfully")
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Transcription failed: {str(e)}"
            )
        
        # Generate quiz with error handling
        try:
            quiz_text = generate_quiz(transcript)
            quiz_questions = parse_quiz_questions(quiz_text)
            logger.info(f"Generated {len(quiz_questions)} quiz questions")
        except Exception as e:
            logger.error(f"Quiz generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Quiz generation failed: {str(e)}"
            )
        
        return {
            "status": "success",
            "transcript": transcript,
            "quiz": quiz_questions
        }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info("Cleaned up audio file")
            except Exception as e:
                logger.error(f"Failed to clean up audio file: {e}")
