import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://vacbot:vacbot@localhost:5432/vacbot"
    )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    VACANCIES_FILE = os.path.join(DATA_DIR, "vacancies.json")
    PROFILE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profile.json")

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")