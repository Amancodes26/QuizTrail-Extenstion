from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pytube import YouTube
import os
import librosa
import torch
from transformers import Qwen2AudioForConditionalGeneration, AutoProcessor
from pathlib import Path
import random

app = FastAPI()

processor = AutoProcessor.from_pretrained("Qwen/Qwen2-Audio-7B-Instruct")
model = Qwen2AudioForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-Audio-7B-Instruct", device_map="auto"
)

class VideoRequest(BaseModel):
    video_url: str

def download_audio(video_url: str):
    yt = YouTube(video_url)
    audio_stream = yt.streams.filter(only_audio=True).first()
    output_file = audio_stream.download(filename="video_audio.mp4")
    return output_file

def transcribe_audio(audio_path: str):
    y, sr = librosa.load(audio_path, sr=processor.feature_extractor.sampling_rate)

    conversation = [{"role": "user", "content": [{"type": "audio", "audio_url": audio_path}]}]

    text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    inputs = processor(text=text, audios=[y], return_tensors="pt", padding=True)
    inputs.input_ids = inputs.input_ids.to("cuda")

    generate_ids = model.generate(**inputs, max_length=1024)
    response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    return response

def generate_quiz(text: str):
    sentences = text.split(". ")
    quiz_questions = []
    for _ in range(min(5, len(sentences))):
        sentence = random.choice(sentences)
        question = sentence.replace(" is ", " ______ ").replace(" are ", " ______ ")
        quiz_questions.append({"question": question, "answer": sentence})
    return quiz_questions

@app.post("/transcribe")
async def transcribe(video: VideoRequest):
    try:
        audio_path = download_audio(video.video_url)
        transcript = transcribe_audio(audio_path)
        quiz = generate_quiz(transcript)
        return {"transcript": transcript, "quiz": quiz}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
