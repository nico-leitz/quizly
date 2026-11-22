"""Utility functions for the YouTube-to-Quiz AI pipeline.

Handles YouTube audio extraction via yt-dlp and FFmpeg, local transcription
with Whisper AI, quiz generation via Google Gemini Flash, and atomic
database persistence for Quiz and Question models.
"""

import json
import os
import tempfile

import whisper
import yt_dlp
from django.db import transaction
from google import genai
from google.genai import errors, types

from quiz_app.models import Question, Quiz

_whisper_model = None

FFMPEG_AUDIO_POSTPROCESSOR = {
    "key": "FFmpegExtractAudio",
    "preferredcodec": "mp3",
    "preferredquality": "192",
}

YDL_BASE_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "postprocessors": [FFMPEG_AUDIO_POSTPROCESSOR],
}

GEMINI_FLASH_MODELS = (
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
)

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
    """Load and cache the local Whisper transcription model.

    Returns:
        whisper.Whisper: Cached Whisper 'base' model instance.
    """
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def build_ydl_options(output_dir: str) -> dict:
    """Return yt-dlp options configured for FFmpeg MP3 extraction.

    Args:
        output_dir (str): Target directory for the extracted MP3 file.

    Returns:
        dict: Configuration dictionary for yt_dlp.YoutubeDL.
    """
    return {
        **YDL_BASE_OPTIONS,
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
    }


def download_audio(video_url: str, output_dir: str) -> str:
    """Download a YouTube video and convert its audio to MP3 via FFmpeg.

    Args:
        video_url (str): Valid YouTube video URL.
        output_dir (str): Directory to store the converted MP3 file.

    Returns:
        str: Full file path to the downloaded MP3 file.
    """
    options = build_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video_url])
    return os.path.join(output_dir, "audio.mp3")


def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to plain text using Whisper AI.

    Args:
        audio_path (str): Path to the local MP3 audio file.

    Returns:
        str: Stripped transcript text extracted from the audio.
    """
    model = get_whisper_model()
    result = model.transcribe(audio_path)
    return result["text"].strip()


def build_quiz_prompt(transcript: str) -> str:
    """Insert the transcript text into the Gemini prompt template.

    Args:
        transcript (str): Plain-text video transcript.

    Returns:
        str: Formatted prompt ready for Gemini Flash.
    """
    return QUIZ_PROMPT_TEMPLATE.replace("{transcript}", transcript)


def get_gemini_client() -> genai.Client:
    """Initialize and return a configured Gemini API client.

    Returns:
        genai.Client: Authenticated Google GenAI client instance.

    Raises:
        ValueError: If GEMINI_API_KEY is missing in environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def request_quiz_json(client: genai.Client, prompt: str) -> str:
    """Call Gemini Flash with automatic model fallback on API errors."""
    config = types.GenerateContentConfig(response_mime_type="application/json")
    last_error = None
    for model in GEMINI_FLASH_MODELS:
        try:
            res = client.models.generate_content(
                model=model, contents=prompt, config=config)
            return res.text
        except errors.APIError as exc:
            last_error = exc
    raise last_error


def generate_quiz_from_transcript(transcript: str) -> dict:
    """Generate quiz JSON from a transcript via Gemini Flash.

    Args:
        transcript (str): Plain-text video transcript.
    Returns:
        dict: Parsed quiz data (title, description, questions).
    """
    client = get_gemini_client()
    prompt = build_quiz_prompt(transcript)
    return json.loads(request_quiz_json(client, prompt))


def create_quiz_data_from_youtube(video_url: str) -> dict:
    """Download audio, transcribe it, and generate quiz JSON data.

    Args:
        video_url (str): Valid YouTube video URL.
    Returns:
        dict: Generated quiz data. Raises ValueError if transcript is empty.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = download_audio(video_url, temp_dir)
        transcript = transcribe_audio(audio_path)
    if not transcript:
        raise ValueError("Could not extract transcript from video.")
    return generate_quiz_from_transcript(transcript)


def build_question_objects(quiz: Quiz, questions_data: list) -> list:
    """Build and return unsaved Question instances for a Quiz.

    Args:
        quiz (Quiz): Parent Quiz instance.
        questions_data (list): Question dicts with title, options, answer.
    """
    return [
        Question(
            quiz=quiz, question_title=item["question_title"],
            question_options=item["question_options"], answer=item["answer"],
        ) for item in questions_data
    ]


def create_quiz_record(user, video_url: str, quiz_data: dict) -> Quiz:
    """Create and return a single Quiz database record.

    Args:
        user (User): Authenticated owner of the quiz.
        video_url (str): Source YouTube URL.
        quiz_data (dict): Generated quiz dictionary.
    """
    return Quiz.objects.create(
        user=user,
        title=quiz_data["title"],
        description=quiz_data.get("description", ""),
        video_url=video_url,
    )


def save_quiz_with_questions(user, video_url: str, quiz_data: dict) -> Quiz:
    """Persist a generated Quiz and its Questions atomically.

    Args:
        user (User): Authenticated owner of the quiz.
        video_url (str): Source YouTube URL.
        quiz_data (dict): Generated quiz dictionary.
    """
    with transaction.atomic():
        quiz = create_quiz_record(user, video_url, quiz_data)
        items = quiz_data.get("questions", [])
        Question.objects.bulk_create(build_question_objects(quiz, items))
    return quiz


def create_quiz_from_url(user, video_url: str) -> Quiz:
    """Generate a quiz from a YouTube URL and save it to the database.

    Args:
        user (User): Authenticated owner of the quiz.
        video_url (str): Valid YouTube video URL.

    Returns:
        Quiz: Persisted Quiz model instance with linked questions.
    """
    quiz_data = create_quiz_data_from_youtube(video_url)
    return save_quiz_with_questions(user, video_url, quiz_data)