from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """Store a generated quiz linked to a user and a YouTube video."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        """Return the quiz title as string representation."""
        return self.title


class Question(models.Model):
    """Store a single multiple-choice question belonging to a quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_title = models.CharField(max_length=500)
    question_options = models.JSONField(default=list)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        """Return the question title as string representation."""
        return self.question_title