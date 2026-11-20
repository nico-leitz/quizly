import json
import os
import tempfile
import whisper
import yt_dlp
from google import genai
from google.genai import types

_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def download_audio(video_url: str, output_dir: str) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        return ydl.prepare_filename(info)


def transcribe_audio(audio_path: str) -> str:
    model = get_whisper_model()
    result = model.transcribe(audio_path)
    return result["text"].strip()


def generate_quiz_from_transcript(transcript: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Based on the following transcript, generate a quiz in valid JSON format.

The JSON must strictly follow this structure:
{{
  "title": "Create a concise quiz title based on the topic of the transcript.",
  "description": "Summarize the transcript in no more than 150 characters.",
  "questions": [
    {{
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer from the above options"
    }}
  ]
}}

Requirements:
- Generate 10 questions (or fewer if the transcript is very short).
- Each question must have exactly 4 distinct answer options.
- "answer" must match one of the strings in "question_options" verbatim.
- Write in the same language as the transcript.

Transcript:
{transcript}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    quiz_data = json.loads(response.text)
    return quiz_data


def create_quiz_data_from_youtube(video_url: str) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_audio(video_url, temp_dir)
        transcript = transcribe_audio(audio_path)

    if not transcript:
        raise ValueError("Could not extract transcript from video.")

    return generate_quiz_from_transcript(transcript)