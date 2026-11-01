from flask import Blueprint, jsonify
from services.chesscom_service import ChesscomService, UserNotFoundError, RateLimitError, ChesscomError

chesscom_bp = Blueprint("chesscom", __name__, url_prefix="/api/chesscom")
service = ChesscomService()

@chesscom_bp.route("/<username>/games", methods=["GET"])
def get_user_games(username: str):
    """
    Fetch up to 20 latest games for a Chess.com username.
    """
    try:
        data = service.get_latest_games(username, limit=20)
        return jsonify({
            "success": True,
            "player": data["player"],
            "games": data["games"],
            "total": data["total_fetched"]
        }), 200

    except ValueError as ve:
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400

    except UserNotFoundError as unfe:
        return jsonify({
            "success": False,
            "error": str(unfe)
        }), 404

    except RateLimitError as rle:
        return jsonify({
            "success": False,
            "error": str(rle)
        }), 429

    except ChesscomError as ce:
        return jsonify({
            "success": False,
            "error": str(ce)
        }), 502

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while communicating with Chess.com."
        }), 500
