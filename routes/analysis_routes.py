import uuid
import time
import threading
from flask import Blueprint, request, jsonify
from services.stockfish_service import StockfishService, StockfishNotFoundError
from services.analysis_service import AnalysisService

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")

stockfish_service = StockfishService()
analysis_service = AnalysisService(stockfish_service)

# In-memory thread-safe store for analysis tasks
ANALYSES = {}
ANALYSES_LOCK = threading.Lock()

def cleanup_old_analyses():
    """Remove analyses older than 2 hours to prevent memory bloat."""
    now = time.time()
    with ANALYSES_LOCK:
        expired_ids = [aid for aid, data in ANALYSES.items() if now - data.get("timestamp", 0) > 7200]
        for aid in expired_ids:
            del ANALYSES[aid]

def run_analysis_task(analysis_id: str, pgn_text: str, depth: int):
    """Worker function executed in background thread."""
    def progress_callback(current, total):
        pct = int((current / total) * 100) if total > 0 else 0
        with ANALYSES_LOCK:
            if analysis_id in ANALYSES:
                ANALYSES[analysis_id]["progress"] = pct
                ANALYSES[analysis_id]["current_move"] = current
                ANALYSES[analysis_id]["total_moves"] = total

    try:
        with ANALYSES_LOCK:
            ANALYSES[analysis_id]["status"] = "analyzing"

        result = analysis_service.analyze_game(pgn_text, depth=depth, progress_callback=progress_callback)

        with ANALYSES_LOCK:
            ANALYSES[analysis_id]["status"] = "completed"
            ANALYSES[analysis_id]["progress"] = 100
            ANALYSES[analysis_id]["result"] = result

    except StockfishNotFoundError as snfe:
        with ANALYSES_LOCK:
            ANALYSES[analysis_id]["status"] = "error"
            ANALYSES[analysis_id]["error"] = str(snfe)
            ANALYSES[analysis_id]["stockfish_missing"] = True
    except Exception as e:
        with ANALYSES_LOCK:
            ANALYSES[analysis_id]["status"] = "error"
            ANALYSES[analysis_id]["error"] = f"Analysis error: {str(e)}"

@analysis_bp.route("/stockfish/status", methods=["GET"])
def stockfish_status():
    """Return status and diagnostics for the local Stockfish engine."""
    return jsonify(stockfish_service.get_engine_status()), 200

@analysis_bp.route("/analyze", methods=["POST"])
def start_analysis():
    """
    Initiate game analysis with local Stockfish.
    Returns analysis_id for polling progress and results.
    """
    cleanup_old_analyses()

    if not stockfish_service.is_available():
        return jsonify({
            "success": False,
            "error": "Stockfish engine is not installed or configured on the server.",
            "instructions": stockfish_service.get_engine_status()["instructions"],
            "stockfish_missing": True
        }), 503

    data = request.get_json() or {}
    pgn_text = data.get("pgn")
    depth = data.get("depth", stockfish_service.default_depth)

    if not pgn_text or not pgn_text.strip():
        return jsonify({
            "success": False,
            "error": "No PGN data provided for analysis."
        }), 400

    analysis_id = str(uuid.uuid4())

    with ANALYSES_LOCK:
        ANALYSES[analysis_id] = {
            "status": "queued",
            "progress": 0,
            "current_move": 0,
            "total_moves": 0,
            "result": None,
            "error": None,
            "timestamp": time.time()
        }

    # Start background analysis thread
    thread = threading.Thread(
        target=run_analysis_task,
        args=(analysis_id, pgn_text, depth),
        daemon=True
    )
    thread.start()

    return jsonify({
        "success": True,
        "analysis_id": analysis_id,
        "message": "Analysis started successfully."
    }), 202

@analysis_bp.route("/analyze/result/<analysis_id>", methods=["GET"])
def get_analysis_result(analysis_id: str):
    """
    Poll analysis progress and retrieve final results.
    """
    with ANALYSES_LOCK:
        task = ANALYSES.get(analysis_id)

    if not task:
        return jsonify({
            "success": False,
            "error": "Analysis session not found or expired."
        }), 404

    return jsonify({
        "success": True,
        "status": task["status"],
        "progress": task["progress"],
        "current_move": task.get("current_move", 0),
        "total_moves": task.get("total_moves", 0),
        "result": task.get("result"),
        "error": task.get("error"),
        "stockfish_missing": task.get("stockfish_missing", False)
    }), 200
