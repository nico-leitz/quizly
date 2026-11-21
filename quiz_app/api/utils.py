import json
import os
import tempfile
import whisper
import yt_dlp
from django.db import transaction
from google import genai
from google.genai import types

from quiz_app.models import Question, Quiz

_whisper_model = None

QUIZ_PROMPT_TEMPLATE = (
    "Based on the following transcript, generate a quiz in valid JSON "
    "format using this exact structure:\n"
    '{"title": "Concise quiz title", '
    '"description": "Short summary (max 150 chars)", '
    '"questions": [{"question_title": "Question text", '
    '"question_options": ["Option A", "Option B", '
    '"Option C", "Option D"], '
    '"answer": "Exact matching option"}]}\n'
    "Requirements:\n"
    "- Generate exactly 10 questions.\n"
    "- Each question must have exactly 4 distinct options.\n"
    "- 'answer' must match one string in 'question_options' verbatim.\n"
    "- Write in the same language as the transcript.\n\n"
    "Transcript:\n{transcript}"
)


def get_whisper_model():
    """Load and cache the local Whisper transcription model."""
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def build_ydl_options(output_dir):
    """Return yt-dlp options to extract an MP3 file via FFmpeg."""
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }


def download_audio(video_url, output_dir):
    """Download a YouTube video and convert it to MP3 using FFmpeg."""
    options = build_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video_url])
    return os.path.join(output_dir, "audio.mp3")


def transcribe_audio(audio_path):
    """Transcribe an audio file to plain text using Whisper AI."""
    model = get_whisper_model()
    result = model.transcribe(audio_path)
    return result["text"].strip()


def build_quiz_prompt(transcript):
    """Insert the transcript text into the Gemini prompt template."""
    return QUIZ_PROMPT_TEMPLATE.format(transcript=transcript)


def get_gemini_client():
    """Initialize and return a configured Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def generate_quiz_from_transcript(transcript):
    """Generate quiz JSON data from a transcript via Gemini Flash."""
    client = get_gemini_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_quiz_prompt(transcript),
        config=config,
    )
    return json.loads(response.text)


def create_quiz_data_from_youtube(video_url):
    """Run download, transcription, and Gemini quiz generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_audio(video_url, temp_dir)
        transcript = transcribe_audio(audio_path)
    if not transcript:
        raise ValueError("Could not extract transcript from video.")
    return generate_quiz_from_transcript(transcript)


def build_question_objects(quiz, questions_data):
    """Build unsaved Question instances from generated quiz data."""
    return [
        Question(
            quiz=quiz,
            question_title=item["question_title"],
            question_options=item["question_options"],
            answer=item["answer"],
        )
        for item in questions_data
    ]


def save_quiz_with_questions(user, video_url, quiz_data):
    """Persist a generated Quiz and its Questions atomically."""
    with transaction.atomic():
        quiz = Quiz.objects.create(
            user=user,
            title=quiz_data["title"],
            description=quiz_data.get("description", ""),
            video_url=video_url,
        )
        items = quiz_data.get("questions", [])
        Question.objects.bulk_create(build_question_objects(quiz, items))
    return quiz


def create_quiz_from_url(user, video_url):
    """Generate a quiz from a YouTube URL and save it to the database."""
    quiz_data = create_quiz_data_from_youtube(video_url)
    return save_quiz_with_questions(user, video_url, quiz_data)