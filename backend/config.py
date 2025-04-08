import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Data files
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
GAMES_FILE = os.getenv("GAMES_FILE", os.path.join(DATA_DIR, "allgames.txt"))
TRAIN_TIMES_FILE = os.getenv("TRAIN_TIMES_FILE", os.path.join(DATA_DIR, "fastest_train_times.csv"))

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# CORS settings - updated with all development URLs
CORS_ORIGINS = os.getenv("CORS_ORIGINS", 
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8001,http://127.0.0.1:8001,http://10.0.0.28:8001,"
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://10.0.0.28:5500,http://10.0.0.67:5500,"
    "http://10.0.0.67:8001,http://10.0.0.67:8000,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "null"  # For local file access
).split(",")

ADMIN_API_KEY = "wiz123"

DEFAULT_CITIES = ["Berlin", "Frankfurt", "Munich"]