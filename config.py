import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "chess-analyzer-secret-key-2026")
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {"pgn"}

    # CORS Configuration for Netlify & external frontends
    # Provide comma-separated origins, e.g. "https://my-chess-app.netlify.app,http://localhost:8080"
    # Defaults to "*" to permit all origins during initial setup
    CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "*")
    if CORS_ORIGINS_RAW.strip() == "*":
        CORS_ORIGINS = "*"
    else:
        CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]

    # Chess.com API Settings
    CHESSCOM_API_BASE = "https://api.chess.com/pub"
    CHESSCOM_USER_AGENT = os.environ.get(
        "CHESSCOM_USER_AGENT",
        "ChessAnalyzer/1.0 (Contact: chess-analyzer-app@localhost.local; OpenSource Learning Platform)"
    )
    CHESSCOM_TIMEOUT = 12  # seconds

    # Stockfish Engine Configuration
    # Prioritizes:
    # 1. Environment variable STOCKFISH_PATH
    # 2. Local bundled binary in bin/stockfish.exe (Windows) or bin/stockfish (Linux)
    # 3. Standard Linux system locations (/usr/games/stockfish or /usr/bin/stockfish)
    # 4. System PATH stockfish
    DEFAULT_LOCAL_STOCKFISH_WIN = os.path.join(BASE_DIR, "bin", "stockfish.exe")
    DEFAULT_LOCAL_STOCKFISH_NIX = os.path.join(BASE_DIR, "bin", "stockfish")
    
    @classmethod
    def get_stockfish_path(cls):
        # 1. Explicit environment variable
        env_path = os.environ.get("STOCKFISH_PATH")
        if env_path and os.path.isfile(env_path):
            return env_path
        
        # 2. Local project bin directory
        if os.path.isfile(cls.DEFAULT_LOCAL_STOCKFISH_WIN):
            return cls.DEFAULT_LOCAL_STOCKFISH_WIN
        if os.path.isfile(cls.DEFAULT_LOCAL_STOCKFISH_NIX):
            return cls.DEFAULT_LOCAL_STOCKFISH_NIX
        
        # 3. Standard Linux / Docker package locations (e.g. apt install stockfish)
        for linux_path in [
            "/usr/games/stockfish",
            "/usr/bin/stockfish",
            "/usr/local/bin/stockfish"
        ]:
            if os.path.isfile(linux_path):
                return linux_path
        
        # 4. Check system PATH
        path_in_env = shutil.which("stockfish") or shutil.which("stockfish.exe")
        if path_in_env:
            return path_in_env
            
        return None

    STOCKFISH_DEFAULT_DEPTH = int(os.environ.get("STOCKFISH_DEPTH", 12))
    STOCKFISH_TIME_LIMIT = float(os.environ.get("STOCKFISH_TIME_LIMIT", 0.12))  # seconds per move
    STOCKFISH_THREADS = int(os.environ.get("STOCKFISH_THREADS", 2))
