from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from yt_dlp.utils import DownloadError

from quiz_app.models import Question, Quiz
from quiz_app.services import create_quiz_data_from_youtube

from .permissions import IsQuizOwner
from .serializers import (
    QuizCreateInputSerializer,
    QuizCreateResponseSerializer,
    QuizSerializer,
)


class QuizListCreateView(generics.ListCreateAPIView):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user).prefetch_related("questions")

    def create(self, request, *args, **kwargs):
        input_serializer = QuizCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        video_url = input_serializer.validated_data["url"]

        try:
            quiz_data = create_quiz_data_from_youtube(video_url)
        except DownloadError:
            return Response(
                {"detail": "Could not download video. Please check the YouTube URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Failed to generate quiz: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            quiz = Quiz.objects.create(
                user=request.user,
                title=quiz_data["title"],
                description=quiz_data.get("description", ""),
                video_url=video_url,
            )
            Question.objects.bulk_create(
                [
                    Question(
                        quiz=quiz,
                        question_title=q["question_title"],
                        question_options=q["question_options"],
                        answer=q["answer"],
                    )
                    for q in quiz_data.get("questions", [])
                ]
            )

        output_serializer = QuizCreateResponseSerializer(quiz)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Quiz.objects.prefetch_related("questions")
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ["get", "patch", "delete", "head", "options"]