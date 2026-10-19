"""Keys, model name and limits for the task agent."""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "openai/gpt-oss-120b"
MAX_STEPS = 15
TEMPERATURE = 0.0
MAX_RETRIES = 3

RUNS_DIR = REPO_ROOT / "runs"
