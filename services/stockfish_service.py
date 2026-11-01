import os
import chess
import chess.engine
from config import Config

class StockfishNotFoundError(Exception):
    """Raised when Stockfish executable cannot be found."""
    pass

class StockfishService:
    def __init__(self, engine_path: str = None):
        self.engine_path = engine_path or Config.get_stockfish_path()
        self.default_depth = Config.STOCKFISH_DEFAULT_DEPTH
        self.default_time_limit = Config.STOCKFISH_TIME_LIMIT

    def is_available(self) -> bool:
        """Check if Stockfish binary is present and executable."""
        if not self.engine_path:
            return False
        return os.path.isfile(self.engine_path)

    def get_engine_status(self) -> dict:
        """Return diagnostic status of the Stockfish engine."""
        available = self.is_available()
        return {
            "available": available,
            "path": self.engine_path if available else None,
            "instructions": (
                "Stockfish engine is not configured. Download the Windows binary from "
                "https://stockfishchess.org/download/ and place it inside the 'bin/' folder as 'stockfish.exe', "
                "or set the STOCKFISH_PATH environment variable."
            ) if not available else "Stockfish engine ready."
        }

    def start_engine(self) -> chess.engine.SimpleEngine:
        """Launch UCI engine instance."""
        if not self.is_available():
            raise StockfishNotFoundError(
                "Stockfish chess engine is not installed or located. "
                "Please download Stockfish from https://stockfishchess.org/download/ "
                "and save it as 'bin/stockfish.exe', or set the STOCKFISH_PATH environment variable."
            )

        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            # Set thread limits if supported
            try:
                engine.configure({"Threads": Config.STOCKFISH_THREADS})
            except Exception:
                pass
            return engine
        except Exception as e:
            raise RuntimeError(f"Failed to start Stockfish process at {self.engine_path}: {str(e)}")

    def evaluate_position(self, board: chess.Board, engine: chess.engine.SimpleEngine, depth: int = None, time_limit: float = None) -> dict:
        """
        Evaluate a single chess board position with Stockfish.
        Returns centipawn/mate score from White's POV and player-to-move POV,
        best move in SAN and UCI, and continuation line (PV).
        """
        d = depth or self.default_depth
        t = time_limit or self.default_time_limit

        limit = chess.engine.Limit(depth=d, time=t)
        info = engine.analyse(board, limit)

        pov_score = info.get("score")
        if not pov_score:
            return {
                "score_white_cp": 0,
                "score_turn_cp": 0,
                "display_eval": "0.0",
                "is_mate": False,
                "mate_moves": None,
                "best_move_uci": None,
                "best_move_san": None,
                "continuation": []
            }

        # Score relative to White
        white_score = pov_score.white()
        # Score relative to current player whose turn it is
        turn_score = pov_score.pov(board.turn)

        is_mate = pov_score.is_mate()
        mate_moves = None
        display_eval = ""

        if is_mate:
            mate_moves_white = white_score.mate()
            mate_moves_turn = turn_score.mate()
            mate_moves = mate_moves_turn
            display_eval = f"M{abs(mate_moves_white)}" if mate_moves_white > 0 else f"-M{abs(mate_moves_white)}"
            # Cap centipawns for numerical processing (charts, accuracy)
            score_white_cp = 10000 - abs(mate_moves_white) * 10 if mate_moves_white > 0 else -10000 + abs(mate_moves_white) * 10
            score_turn_cp = 10000 - abs(mate_moves_turn) * 10 if mate_moves_turn > 0 else -10000 + abs(mate_moves_turn) * 10
        else:
            score_white_cp = white_score.score()
            score_turn_cp = turn_score.score()
            # Convert centipawns to pawn unit with sign (e.g., +1.4, -0.6)
            eval_float = score_white_cp / 100.0
            display_eval = f"+{eval_float:.1f}" if eval_float > 0 else f"{eval_float:.1f}"

        # Extract best move and continuation (PV)
        pv = info.get("pv", [])
        best_move_uci = None
        best_move_san = None
        continuation_sans = []

        if pv:
            best_move = pv[0]
            best_move_uci = best_move.uci()
            try:
                best_move_san = board.san(best_move)
            except Exception:
                best_move_san = best_move_uci

            # Convert continuation line to SAN
            temp_board = board.copy()
            for m in pv[:5]:
                try:
                    continuation_sans.append(temp_board.san(m))
                    temp_board.push(m)
                except Exception:
                    break

        return {
            "score_white_cp": score_white_cp,
            "score_turn_cp": score_turn_cp,
            "display_eval": display_eval,
            "is_mate": is_mate,
            "mate_moves": mate_moves,
            "best_move_uci": best_move_uci,
            "best_move_san": best_move_san,
            "continuation": continuation_sans,
            "depth": info.get("depth", d)
        }
