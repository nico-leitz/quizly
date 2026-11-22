"""Automated API, model, and utility tests for quiz_app."""

import json
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from yt_dlp.utils import DownloadError

from quiz_app.api import utils
from quiz_app.models import Question, Quiz

MOCK_QUIZ_DATA = {
    "title": "Python Basics Quiz",
    "description": "Short quiz about Python fundamentals.",
    "questions": [
        {
            "question_title": "What is a list in Python?",
            "question_options": ["Mutable", "Immutable", "Loop", "Class"],
            "answer": "Mutable",
        }
    ],
}


@override_settings(AUTH_COOKIE_SECURE=False)
class QuizApiTests(APITestCase):
    """Test suite for all quiz_app CRUD and generation endpoints."""

    def setUp(self):
        """Create two users and sample quizzes for permission checks."""
        self.owner = self.create_user("owner", "owner@example.com")
        self.other = self.create_user("other", "other@example.com")
        self.quiz = self.create_quiz(self.owner, "Owner Quiz")
        self.other_quiz = self.create_quiz(self.other, "Other Quiz")
        self.list_url = reverse("quiz-list-create")

    def create_user(self, username, email):
        """Create and return a Django user."""
        return User.objects.create_user(
            username=username, email=email, password="TestPassword123!"
        )

    def create_quiz(self, user, title):
        """Create a quiz with one question for a given user."""
        quiz = Quiz.objects.create(
            user=user, title=title, description="Sample description",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        Question.objects.create(
            quiz=quiz, question_title="Sample Question?",
            question_options=["A", "B", "C", "D"], answer="A",
        )
        return quiz

    def authenticate(self, user):
        """Set a valid access_token cookie for the given user."""
        token = str(RefreshToken.for_user(user).access_token)
        self.client.cookies["access_token"] = token

    def detail_url(self, quiz_id):
        """Return the detail URL for a given quiz ID."""
        return reverse("quiz-detail", kwargs={"pk": quiz_id})

    @patch("quiz_app.api.utils.create_quiz_data_from_youtube")
    def test_create_quiz_success(self, mock_generate):
        """Valid YouTube URL returns 201 with question timestamps."""
        mock_generate.return_value = MOCK_QUIZ_DATA
        self.authenticate(self.owner)
        payload = {"url": "https://www.youtube.com/watch?v=example"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Python Basics Quiz")
        self.assertIn("created_at", res.data["questions"][0])
        self.assertIn("updated_at", res.data["questions"][0])

    def test_create_quiz_invalid_url(self):
        """Non-YouTube URL returns 400 Bad Request."""
        self.authenticate(self.owner)
        payload = {"url": "https://example.com/video"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("quiz_app.api.utils.create_quiz_data_from_youtube")
    def test_create_quiz_download_error(self, mock_generate):
        """YouTube DownloadError returns 400 Bad Request."""
        mock_generate.side_effect = DownloadError("Unavailable")
        self.authenticate(self.owner)
        payload = {"url": "https://www.youtube.com/watch?v=broken"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("quiz_app.api.utils.create_quiz_data_from_youtube")
    def test_create_quiz_internal_error(self, mock_generate):
        """Unexpected pipeline errors return 500 Internal Server Error."""
        mock_generate.side_effect = RuntimeError("API failure")
        self.authenticate(self.owner)
        payload = {"url": "https://www.youtube.com/watch?v=example"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, 500)

    def test_create_quiz_unauthenticated(self):
        """Unauthenticated POST returns 401 Unauthorized."""
        payload = {"url": "https://www.youtube.com/watch?v=example"}
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_quizzes_returns_only_own(self):
        """GET /api/quizzes/ lists only own quizzes without q-timestamps."""
        self.authenticate(self.owner)
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Owner Quiz")
        self.assertNotIn("created_at", res.data[0]["questions"][0])

    def test_list_quizzes_unauthenticated(self):
        """Unauthenticated GET /api/quizzes/ returns 401 Unauthorized."""
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_own_quiz(self):
        """Owner can retrieve their own quiz with 200 OK."""
        self.authenticate(self.owner)
        res = self.client.get(self.detail_url(self.quiz.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.quiz.id)

    def test_retrieve_other_users_quiz_forbidden(self):
        """Accessing another user's quiz returns 403 Forbidden."""
        self.authenticate(self.owner)
        res = self.client.get(self.detail_url(self.other_quiz.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_nonexistent_quiz_not_found(self):
        """Requesting a missing quiz ID returns 404 Not Found."""
        self.authenticate(self.owner)
        res = self.client.get(self.detail_url(99999))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_own_quiz(self):
        """Owner can partially update title and description."""
        self.authenticate(self.owner)
        payload = {"title": "Updated Title", "description": "New Desc"}
        res = self.client.patch(
            self.detail_url(self.quiz.id), payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Updated Title")
        self.assertEqual(res.data["description"], "New Desc")

    def test_patch_invalid_data(self):
        """Empty title on PATCH returns 400 Bad Request."""
        self.authenticate(self.owner)
        res = self.client.patch(
            self.detail_url(self.quiz.id), {"title": ""}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_other_users_quiz_forbidden(self):
        """Patching another user's quiz returns 403 Forbidden."""
        self.authenticate(self.owner)
        res = self.client.patch(
            self.detail_url(self.other_quiz.id),
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_quiz_cascades_questions(self):
        """Deleting own quiz returns 204 and removes linked questions."""
        self.authenticate(self.owner)
        res = self.client.delete(self.detail_url(self.quiz.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())
        self.assertEqual(Question.objects.filter(quiz=self.quiz).count(), 0)

    def test_delete_other_users_quiz_forbidden(self):
        """Deleting another user's quiz returns 403 Forbidden."""
        self.authenticate(self.owner)
        res = self.client.delete(self.detail_url(self.other_quiz.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_quiz_not_found(self):
        """Deleting a missing quiz ID returns 404 Not Found."""
        self.authenticate(self.owner)
        res = self.client.delete(self.detail_url(99999))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_unauthenticated(self):
        """Unauthenticated GET/PATCH/DELETE on detail return 401."""
        url = self.detail_url(self.quiz.id)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.patch(url, {}).status_code, 401)
        self.assertEqual(self.client.delete(url).status_code, 401)


class QuizUtilsAndModelTests(TestCase):
    """Unit tests for model string methods and quiz_app pipeline utils."""

    def test_model_str_representations(self):
        """Quiz and Question __str__ methods return their titles."""
        user = User.objects.create_user(username="u1", password="pw123456!")
        quiz = Quiz.objects.create(
            user=user, title="My Quiz", video_url="https://youtu.be/abc"
        )
        question = Question.objects.create(
            quiz=quiz, question_title="My Q?", answer="A"
        )
        self.assertEqual(str(quiz), "My Quiz")
        self.assertEqual(str(question), "My Q?")

    @patch("quiz_app.api.utils.whisper.load_model")
    def test_get_whisper_model_caches_instance(self, mock_load):
        """Whisper model is loaded once and cached for subsequent calls."""
        utils._whisper_model = None
        self.addCleanup(setattr, utils, "_whisper_model", None)
        first = utils.get_whisper_model()
        second = utils.get_whisper_model()
        self.assertIs(first, second)
        mock_load.assert_called_once_with("base")

    @patch("quiz_app.api.utils.yt_dlp.YoutubeDL")
    def test_download_audio_returns_mp3_path(self, mock_ydl_cls):
        """download_audio invokes yt-dlp and returns the MP3 file path."""
        mock_ydl = mock_ydl_cls.return_value.__enter__.return_value
        path = utils.download_audio("https://youtu.be/abc", "/tmp")
        mock_ydl.download.assert_called_once_with(["https://youtu.be/abc"])
        self.assertEqual(path, os.path.join("/tmp", "audio.mp3"))

    @patch("quiz_app.api.utils.get_whisper_model")
    def test_transcribe_audio_strips_text(self, mock_get_model):
        """transcribe_audio returns stripped transcript text."""
        mock_model = mock_get_model.return_value
        mock_model.transcribe.return_value = {"text": "  Hello world  "}
        result = utils.transcribe_audio("/tmp/audio.mp3")
        self.assertEqual(result, "Hello world")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_gemini_client_missing_api_key(self):
        """Missing GEMINI_API_KEY raises a ValueError."""
        with self.assertRaises(ValueError):
            utils.get_gemini_client()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"})
    @patch("quiz_app.api.utils.genai.Client")
    def test_generate_quiz_from_transcript(self, mock_client_cls):
        """Gemini response JSON is parsed into a quiz dictionary."""
        mock_response = MagicMock(text=json.dumps(MOCK_QUIZ_DATA))
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = mock_response
        result = utils.generate_quiz_from_transcript("Python transcript")
        self.assertEqual(result["title"], "Python Basics Quiz")

    @patch("quiz_app.api.utils.generate_quiz_from_transcript")
    @patch("quiz_app.api.utils.transcribe_audio")
    @patch("quiz_app.api.utils.download_audio")
    def test_create_quiz_data_from_youtube_success(
        self, mock_dl, mock_tr, mock_gen
    ):
        """Pipeline orchestrates download, transcription, and generation."""
        mock_dl.return_value = "/tmp/audio.mp3"
        mock_tr.return_value = "Sample transcript"
        mock_gen.return_value = MOCK_QUIZ_DATA
        result = utils.create_quiz_data_from_youtube("https://youtu.be/abc")
        self.assertEqual(result, MOCK_QUIZ_DATA)

    @patch("quiz_app.api.utils.transcribe_audio", return_value="")
    @patch("quiz_app.api.utils.download_audio", return_value="/tmp/a.mp3")
    def test_create_quiz_data_empty_transcript(self, mock_dl, mock_tr):
        """Empty transcript raises a ValueError."""
        with self.assertRaises(ValueError):
            utils.create_quiz_data_from_youtube("https://youtu.be/abc")
        mock_dl.assert_called_once()
        mock_tr.assert_called_once()