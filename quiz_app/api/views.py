"""API views for generating and managing user quizzes."""

import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quiz_app.models import Quiz

from .permissions import IsQuizOwner
from .serializers import (
    QuizCreateInputSerializer,
    QuizCreateResponseSerializer,
    QuizSerializer,
)
from .utils import create_quiz_from_url

logger = logging.getLogger(__name__)


class QuizListCreateView(generics.ListCreateAPIView):
    """List user quizzes or generate a new quiz from a YouTube URL."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use URL input serializer for POST and QuizSerializer for GET."""
        if self.request.method == "POST":
            return QuizCreateInputSerializer
        return QuizSerializer

    def get_queryset(self):
        """Return only quizzes owned by the authenticated user."""
        return Quiz.objects.filter(
            user=self.request.user
        ).prefetch_related("questions")

    def post(self, request):
        """Validate URL, generate a quiz via AI, and return it."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            url = serializer.validated_data["url"]
            quiz = create_quiz_from_url(request.user, url)
        except DownloadError:
            return Response({"detail": "Invalid YouTube URL."}, status=400)
        except Exception:
            logger.exception("Quiz generation failed.")
            return Response({"detail": "Quiz generation failed."}, status=500)
        data = QuizCreateResponseSerializer(quiz).data
        return Response(data, status=status.HTTP_201_CREATED)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update, or delete a single user-owned quiz."""

    queryset = Quiz.objects.prefetch_related("questions")
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ["get", "patch", "delete", "head", "options"]