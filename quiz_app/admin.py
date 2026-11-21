from django.contrib import admin
from .models import Question, Quiz


class QuestionInline(admin.TabularInline):
    """Allow editing quiz questions directly inside a Quiz admin page."""

    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin configuration for managing quizzes."""

    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("user", "created_at")
    search_fields = ("title", "description", "video_url")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin configuration for managing individual quiz questions."""

    list_display = ("id", "question_title", "quiz", "answer")
    list_filter = ("quiz",)
    search_fields = ("question_title", "answer")