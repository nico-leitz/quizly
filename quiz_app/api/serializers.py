from urllib.parse import urlparse
from rest_framework import serializers
from quiz_app.models import Question, Quiz

ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}


class QuestionSerializer(serializers.ModelSerializer):
    """Serialize a question for GET and PATCH quiz responses."""

    class Meta:
        model = Question
        fields = ["id", "question_title", "question_options", "answer"]


class QuestionCreateResponseSerializer(serializers.ModelSerializer):
    """Serialize a question with timestamps for POST quiz responses."""

    class Meta:
        model = Question
        fields = [
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Serialize a quiz for listing, detail view, and partial updates."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]


class QuizCreateResponseSerializer(serializers.ModelSerializer):
    """Serialize a newly created quiz including question timestamps."""

    questions = QuestionCreateResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]


class QuizCreateInputSerializer(serializers.Serializer):
    """Validate the YouTube URL submitted for quiz generation."""

    url = serializers.URLField()

    def validate_url(self, value):
        """Ensure the submitted URL points to a valid YouTube domain."""
        host = urlparse(value).netloc.lower()
        if host not in ALLOWED_YOUTUBE_HOSTS:
            raise serializers.ValidationError(
                "Please provide a valid YouTube URL."
            )
        return value