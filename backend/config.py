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

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")