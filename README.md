<div align="center">

# Quizly - AI-Powered YouTube Quiz API

*A secure, modern REST API that transforms YouTube videos into interactive multiple-choice quizzes using Django, Django REST Framework, Whisper AI, and Google Gemini Flash*

<br>

![Python](https://img.shields.io/badge/PYTHON-3.12%2B-007ec6?style=for-the-badge&labelColor=555555)
![Django](https://img.shields.io/badge/DJANGO-6.1-51a825?style=for-the-badge&labelColor=555555)
![DRF](https://img.shields.io/badge/DRF-3.15-e04343?style=for-the-badge&labelColor=555555)

</div>

---

## Overview

Quizly allows authenticated users to submit any YouTube URL and automatically generate a 10-question multiple-choice quiz based on the video's spoken content. The backend handles audio extraction, local speech-to-text transcription, AI quiz generation, and full quiz management with strict ownership permissions and HTTP-only JWT cookie authentication.

## Features

- **Cookie-Based JWT Authentication:** Secure registration, login, token refresh, and logout using `djangorestframework-simplejwt` with HTTP-only cookies and server-side refresh token blacklisting
- **YouTube Audio Extraction:** Extracts audio tracks exclusively from validated YouTube URLs using `yt-dlp` and converts them to MP3 via `FFmpeg`
- **Local Speech-to-Text Transcription:** Transcribes extracted audio locally with OpenAI `Whisper`
- **AI Quiz Generation:** Uses `Google Gemini Flash` (`google-genai`) to generate structured 10-question quizzes with 4 answer options per question in the video's language
- **Quiz Management (CRUD):** Full support for generating, listing, retrieving, partially updating (`title`, `description`), and permanently deleting quizzes with strict owner-only access (`403 Forbidden` for unauthorized access)
- **Django Admin Panel:** Configured admin interface supporting inline editing of quizzes and individual questions
- **Optimized Queries:** Uses `prefetch_related()` and atomic database transactions to ensure data integrity and prevent N+1 query issues
- **Automated Testing:** Test suite covering authentication, permissions, and quiz endpoints with mocked AI pipeline execution

## Technologies Used

- **Language:** Python 3.12+
- **Framework:** Django 6.1 & Django REST Framework (DRF)
- **Authentication:** `djangorestframework-simplejwt` (HTTP-only cookies + Token Blacklist)
- **Media & AI Pipeline:** `yt-dlp`, `FFmpeg`, OpenAI `Whisper`, `google-genai` (Gemini Flash)
- **Configuration & Security:** `django-cors-headers`, `python-dotenv`
- **Database:** SQLite (Default, easily configurable)

## Project Structure

```text
quizly_backend/
│
├── core/                  # Centralized Django settings and main URL routing
├── user_auth/             # Cookie-based JWT authentication app
│   └── api/               # API layer (views.py, serializers.py, urls.py, permissions.py, authentication.py, utils.py)
├── quiz_app/              # AI quiz generation, quiz & question management app
│   └── api/               # API layer (views.py, serializers.py, urls.py, permissions.py, utils.py)
├── .env.example           # Environment variables template
└── requirements.txt       # Project dependencies
```

## Prerequisites

Before setting up the project, make sure the following requirements are met:

- **FFmpeg (Required Globally):** Both `Whisper AI` and `yt-dlp` require `FFmpeg` to be installed globally on your system and accessible via your system `PATH`.
  - **Ubuntu / Debian / WSL:**
    ```bash
    sudo apt update && sudo apt install -y ffmpeg
    ```
  - **macOS (Homebrew):**
    ```bash
    brew install ffmpeg
    ```
  - **Windows (winget):**
    ```bash
    winget install Gyan.FFmpeg
    ```
  *Verify installation with `ffmpeg -version`.*
- **Google Gemini API Key:** A free API key from [Google AI Studio](https://aistudio.google.com/) is required for quiz generation.

## Installation & Setup

*Note: On macOS and Linux, you may need to use `python3` and `pip3` instead of `python` and `pip`.*

### 1. Clone the repository
```bash
git clone https://github.com/nico-leitz/quizly_backend.git
cd quizly_backend
```

### 2. Create and activate a virtual environment
- **Windows (Command Prompt / PowerShell):**
  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  ```
- **macOS / Linux / WSL:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
*(Make sure `(.venv)` appears at the beginning of your terminal line)*

### 3. Install dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure environment variables (`.env`)
Copy the provided `.env.example` template to create your local `.env` file:
- **Windows:**
  ```bash
  copy .env.example .env
  ```
- **macOS / Linux / WSL:**
  ```bash
  cp .env.example .env
  ```

Fill in the required values inside `.env`:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
COOKIE_SECURE=False
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
GEMINI_API_KEY=your-gemini-api-key-here
```

*(Optional) Generate a fresh, secure `SECRET_KEY` to paste into your `.env`:*
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Apply database migrations
```bash
python manage.py migrate
```

### 6. Create an admin superuser (Optional)
```bash
python manage.py createsuperuser
```
*Allows access to the Django Admin Panel at `http://127.0.0.1:8000/admin/` to view and edit quizzes and questions.*

### 7. Start the development server
```bash
python manage.py runserver
```
The API is now running locally at `http://127.0.0.1:8000/api/`. Keep this terminal window open!

## Running Tests & Coverage

To run the automated test suite and check test coverage:

```bash
coverage run --source='user_auth,quiz_app' manage.py test
coverage report -m
```

## Core API Endpoints

### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/register/` | Register a new user account with password confirmation and email validation |
| `POST` | `/api/login/` | Authenticate a user and set `access_token` and `refresh_token` as HTTP-only cookies |
| `POST` | `/api/logout/` | Blacklist the refresh token and delete all auth cookies (Authenticated users only) |
| `POST` | `/api/token/refresh/` | Issue a new `access_token` cookie using a valid `refresh_token` cookie |

### Quiz Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/quizzes/` | Generate and store a new 10-question quiz from a YouTube URL (Authenticated users only) |
| `GET` | `/api/quizzes/` | List all quizzes with questions belonging to the authenticated user |
| `GET` | `/api/quizzes/{id}/` | Retrieve a specific quiz with all questions (Quiz owner only) |
| `PATCH` | `/api/quizzes/{id}/` | Partially update `title` and/or `description` of a quiz (Quiz owner only) |
| `DELETE` | `/api/quizzes/{id}/` | Permanently delete a quiz and all associated questions (Quiz owner only) |