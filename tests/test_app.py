import unittest
import json
import time
import io
import chess
from app import create_app
from services.chesscom_service import ChesscomService
from services.pgn_service import PGNService, PGNError
from services.stockfish_service import StockfishService
from services.analysis_service import AnalysisService

SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2026.10.15"]
[White "GrandmasterA"]
[Black "GrandmasterB"]
[Result "1-0"]
[WhiteElo "2700"]
[BlackElo "2680"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0"""

MULTI_GAME_PGN = """[Event "Game 1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0

[Event "Game 2"]
[White "Player3"]
[Black "Player4"]
[Result "0-1"]

1. d4 d5 2. c4 c6 0-1"""

class TestChessAnalyzer(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_stockfish_status_api(self):
        """Test Stockfish status diagnostic endpoint."""
        resp = self.client.get("/api/stockfish/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("available"))
        self.assertIsNotNone(data.get("path"))

    def test_chesscom_username_validation(self):
        """Test username validation logic."""
        self.assertEqual(ChesscomService.validate_username("MagnusCarlsen"), "magnuscarlsen")
        self.assertEqual(ChesscomService.validate_username("user_123-test"), "user_123-test")
        
        with self.assertRaises(ValueError):
            ChesscomService.validate_username("ab")  # too short
        with self.assertRaises(ValueError):
            ChesscomService.validate_username("user!@#$%")  # illegal characters

    def test_chesscom_api_invalid_username(self):
        """Test Chess.com API returns 400 for illegal username."""
        resp = self.client.get("/api/chesscom/a!/games")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_pgn_service_parsing(self):
        """Test single and multi-game PGN extraction."""
        games = PGNService.parse_pgn_text(SAMPLE_PGN)
        self.assertEqual(len(games), 1)
        g = games[0]
        self.assertEqual(g["white"]["username"], "GrandmasterA")
        self.assertEqual(g["black"]["username"], "GrandmasterB")
        self.assertEqual(g["moves_count"], 20)

        # Multi-game test
        multi_games = PGNService.parse_pgn_text(MULTI_GAME_PGN)
        self.assertEqual(len(multi_games), 2)
        self.assertEqual(multi_games[0]["white"]["username"], "Player1")
        self.assertEqual(multi_games[1]["white"]["username"], "Player3")

    def test_pgn_upload_endpoint_json(self):
        """Test /api/pgn/upload via JSON payload."""
        resp = self.client.post("/api/pgn/upload", json={"pgn": SAMPLE_PGN})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["games_count"], 1)

    def test_pgn_upload_endpoint_file(self):
        """Test /api/pgn/upload via multipart file upload."""
        data = {
            "file": (io.BytesIO(SAMPLE_PGN.encode("utf-8")), "test_game.pgn")
        }
        resp = self.client.post("/api/pgn/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["games_count"], 1)

    def test_stockfish_evaluation(self):
        """Test direct Stockfish UCI evaluation."""
        sf = StockfishService()
        self.assertTrue(sf.is_available())
        engine = sf.start_engine()
        try:
            board = chess.Board()
            eval_res = sf.evaluate_position(board, engine, depth=8)
            self.assertIn("score_white_cp", eval_res)
            self.assertIn("display_eval", eval_res)
            self.assertIn("best_move_san", eval_res)
        finally:
            engine.quit()

    def test_game_analysis_and_report(self):
        """Test full move-by-move Stockfish analysis pipeline."""
        analysis_service = AnalysisService()
        mini_pgn = """[Event "Mini Game"]
[White "Player 1"]
[Black "Player 2"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"""

        result = analysis_service.analyze_game(mini_pgn, depth=8)
        self.assertIn("moves", result)
        self.assertIn("report", result)
        self.assertEqual(result["total_moves"], 7)

        report = result["report"]
        self.assertIn("white_accuracy", report)
        self.assertIn("black_accuracy", report)
        self.assertIn("white_stats", report)
        self.assertIn("black_stats", report)
        self.assertIn("critical_moments", report)

        # Black played 3... Nf6 allowing Scholar's mate, which must be classified as a blunder
        self.assertGreaterEqual(report["black_stats"]["Blunder"], 1)

    def test_async_analysis_api_polling(self):
        """Test /api/analyze and polling /api/analyze/result/<id>."""
        short_pgn = """[Event "Quick Test"]
[White "A"]
[Black "B"]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nc6 1/2-1/2"""

        post_resp = self.client.post("/api/analyze", json={"pgn": short_pgn, "depth": 8})
        self.assertEqual(post_resp.status_code, 202)
        post_data = post_resp.get_json()
        analysis_id = post_data["analysis_id"]

        # Poll until complete (with max 10s timeout)
        completed = False
        for _ in range(20):
            poll_resp = self.client.get(f"/api/analyze/result/{analysis_id}")
            self.assertEqual(poll_resp.status_code, 200)
            poll_data = poll_resp.get_json()
            if poll_data["status"] == "completed":
                completed = True
                self.assertIsNotNone(poll_data["result"])
                break
            time.sleep(0.5)

        self.assertTrue(completed, "Analysis task did not finish in time")

    def test_api_health_endpoint(self):
        """Test /api/health endpoint for Render container checks."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("stockfish", data)

    def test_cors_headers_and_preflight(self):
        """Test Flask-CORS headers allow Netlify domain."""
        origin = "https://chess-analyzer-demo.netlify.app"
        
        # Test GET request with Netlify Origin
        resp = self.client.get("/api/stockfish/status", headers={"Origin": origin})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        self.assertIn(resp.headers["Access-Control-Allow-Origin"], [origin, "*"])

        # Test preflight OPTIONS request
        options_resp = self.client.options(
            "/api/analyze",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        self.assertEqual(options_resp.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", options_resp.headers)
        self.assertIn("POST", options_resp.headers.get("Access-Control-Allow-Methods", ""))

if __name__ == "__main__":
    unittest.main()

