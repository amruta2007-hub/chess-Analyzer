from flask import Blueprint, request, jsonify
from services.pgn_service import PGNService, PGNError

pgn_bp = Blueprint("pgn", __name__, url_prefix="/api/pgn")

@pgn_bp.route("/upload", methods=["POST"])
def upload_pgn():
    """
    Handle PGN file upload or raw PGN string submission.
    Parses and returns structured game list.
    """
    try:
        pgn_text = None

        # Check multipart file upload
        if "file" in request.files:
            file_obj = request.files["file"]
            pgn_text = PGNService.validate_and_read_content(file_obj)

        # Check JSON payload
        elif request.is_json:
            data = request.get_json() or {}
            pgn_text = data.get("pgn_text") or data.get("pgn")
            if not pgn_text:
                return jsonify({"success": False, "error": "No PGN text provided in JSON payload."}), 400

        # Check form data
        elif "pgn_text" in request.form:
            pgn_text = request.form["pgn_text"]

        else:
            return jsonify({
                "success": False,
                "error": "No PGN file or text found. Please upload a .pgn file or paste PGN text."
            }), 400

        games = PGNService.parse_pgn_text(pgn_text)
        return jsonify({
            "success": True,
            "games_count": len(games),
            "games": games
        }), 200

    except PGNError as pe:
        return jsonify({
            "success": False,
            "error": str(pe)
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to process PGN: {str(e)}"
        }), 500
