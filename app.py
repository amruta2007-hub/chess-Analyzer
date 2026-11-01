import os
from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_cors import CORS
from config import Config
from routes.chesscom_routes import chesscom_bp
from routes.pgn_routes import pgn_bp
from routes.analysis_routes import analysis_bp
from services.stockfish_service import StockfishService

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # Configure CORS for all /api/* routes to allow Netlify frontend & local development
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=True,
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"]
    )

    # Ensure uploads directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register API blueprints
    app.register_blueprint(chesscom_bp)
    app.register_blueprint(pgn_bp)
    app.register_blueprint(analysis_bp)

    # Root API & Health Check Endpoint (Essential for Render / Docker deployment)
    @app.route("/api/health")
    def api_health():
        stockfish_info = StockfishService().get_engine_status()
        return jsonify({
            "status": "healthy",
            "service": "Chess Analyzer API",
            "stockfish": stockfish_info
        }), 200

    # Frontend Page Routes (Serves Jinja templates if rendered directly, or JSON for API clients)
    @app.route("/")
    def index():
        stockfish_info = StockfishService().get_engine_status()
        # If client accepts JSON or requests via API client, return health JSON
        if request.accept_mimetypes.best == "application/json" and not request.accept_mimetypes.accept_html:
            return jsonify({
                "status": "online",
                "service": "Chess Analyzer Backend API",
                "stockfish": stockfish_info
            }), 200
        try:
            return render_template("index.html", stockfish_info=stockfish_info)
        except Exception:
            return jsonify({
                "status": "online",
                "service": "Chess Analyzer Backend API",
                "stockfish": stockfish_info
            }), 200

    @app.route("/games")
    def games():
        try:
            return render_template("games.html")
        except Exception:
            return jsonify({"status": "ok", "route": "games"}), 200

    @app.route("/analysis")
    def analysis():
        stockfish_info = StockfishService().get_engine_status()
        try:
            return render_template("analysis.html", stockfish_info=stockfish_info)
        except Exception:
            return jsonify({"status": "ok", "route": "analysis", "stockfish": stockfish_info}), 200

    @app.route("/report")
    def report():
        try:
            return render_template("report.html")
        except Exception:
            return jsonify({"status": "ok", "route": "report"}), 200

    @app.route("/about")
    def about():
        try:
            return render_template("about.html")
        except Exception:
            return jsonify({"status": "ok", "route": "about"}), 200

    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found"}), 404
        try:
            return render_template("base.html", error_message="Page Not Found (404)"), 404
        except Exception:
            return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"success": False, "error": "File exceeds the 5MB upload limit."}), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
