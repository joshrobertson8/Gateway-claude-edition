import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gateway.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBt6QH_pm40trJptafU1w7F0vfAIfnEOIs")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
)
PROBLEMS_PER_ACTIVITY = int(os.getenv("PROBLEMS_PER_ACTIVITY", "3"))
