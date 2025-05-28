import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).parent

# Load environment variables from .env file with explicit path
env_file = BASE_DIR / '.env'
load_dotenv(env_file)

# Print debug info to see if .env file is found
print(f"Looking for .env file at: {env_file}")
print(f".env file exists: {env_file.exists()}")

# Data files
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
GAMES_FILE = os.getenv("GAMES_FILE", os.path.join(DATA_DIR, "allgames.txt"))
TRAIN_TIMES_FILE = os.getenv("TRAIN_TIMES_FILE", os.path.join(DATA_DIR, "fastest_train_times.csv"))

# Debug: Print what we're loading
print(f"SUPABASE_URL loaded: {bool(os.getenv('SUPABASE_URL'))}")
print(f"JWT_SECRET loaded: {bool(os.getenv('JWT_SECRET'))}")

# Supabase Configuration - REQUIRED
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Security - REQUIRED, NO FALLBACKS
JWT_SECRET = os.getenv("JWT_SECRET")

# Server settings
API_HOST = os.getenv("HOST", "10.0.0.28")
API_PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# CORS settings - updated with all development URLs
CORS_ORIGINS = os.getenv("CORS_ORIGINS", 
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8001,http://127.0.0.1:8001,"
    "http://172.30.2.216:8001,http://172.30.2.216:8000,"
    "http://10.0.0.28:8001,http://10.0.0.28:5500,"
    "http://10.0.0.67:5500,http://10.0.0.67:8001,http://10.0.0.67:8000,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "null"
).split(",")

# Validation - Fail fast if critical config is missing
def validate_config():
    """Validate that all required configuration is present"""
    missing = []
    
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not JWT_SECRET:
        missing.append("JWT_SECRET")
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Config file directory: {BASE_DIR}")
        print(f".env file path: {env_file}")
        print(f".env file exists: {env_file.exists()}")
        
        # Try to read .env file manually for debugging
        if env_file.exists():
            print("Contents of .env file:")
            try:
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines[:5], 1):  # Show first 5 lines
                        print(f"  Line {i}: {line.strip()}")
            except Exception as e:
                print(f"  Error reading .env file: {e}")
        
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Security checks
    if len(JWT_SECRET) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")
    
    print("✅ Configuration validation passed")

# Run validation on import
validate_config()

# Default cities
DEFAULT_CITIES = ["Berlin", "Frankfurt", "Munich"]