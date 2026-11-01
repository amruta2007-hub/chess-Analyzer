import math
import chess
import chess.pgn
import io
from services.stockfish_service import StockfishService

class AnalysisService:
    def __init__(self, stockfish_service: StockfishService = None):
        self.stockfish_service = stockfish_service or StockfishService()

    @staticmethod
    def win_probability(cp: float) -> float:
        """
        Convert centipawn evaluation to winning percentage (0 to 100).
        Uses standard logistic model.
        """
        # Cap cp for numerical stability
        clamped_cp = max(-1500, min(1500, cp))
        return 100.0 / (1.0 + math.exp(-0.00368208 * clamped_cp))

    @staticmethod
    def calculate_move_accuracy(win_prob_before: float, win_prob_after: float) -> float:
        """
        Compute move accuracy percentage based on win probability loss.
        """
        prob_loss = max(0.0, win_prob_before - win_prob_after)
        # Formula modeling accuracy drop
        accuracy = 103.1668 * math.exp(-0.04354 * prob_loss) - 3.1669
        return max(0.0, min(100.0, accuracy))

    @staticmethod
    def is_sacrifice(board_before: chess.Board, move: chess.Move) -> bool:
        """
        Detect if a move is a sacrifice (gives up a higher value piece or leaves piece en prise).
        """
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }
        moving_piece = board_before.piece_at(move.from_square)
        if not moving_piece:
            return False

        moving_val = piece_values.get(moving_piece.piece_type, 0)
        dest_piece = board_before.piece_at(move.to_square)
        dest_val = piece_values.get(dest_piece.piece_type, 0) if dest_piece else 0

        # If giving up a piece for nothing or for lesser material
        if moving_val > 1 and moving_val > (dest_val + 1):
            # Check if destination square is attacked by opponent
            if board_before.is_attacked_by(not board_before.turn, move.to_square):
                return True
        return False

    def classify_move(self, board_before: chess.Board, played_move: chess.Move,
                      eval_loss_cp: float, best_move_uci: str,
                      turn_score_after: float, is_mate: bool) -> tuple:
        """
        Classify move into:
        - Brilliant (!!)
        - Best (★)
        - Excellent (✓)
        - Good
        - Inaccuracy (?!)
        - Mistake (?)
        - Blunder (??)
        Returns (classification_name, badge_symbol, explanation_string)
        """
        is_best = (played_move.uci() == best_move_uci) or (eval_loss_cp <= 12)
        has_sacrifice = self.is_sacrifice(board_before, played_move)

        # Brilliant: Best move involving a tactical piece sacrifice maintaining winning position
        if is_best and has_sacrifice and (turn_score_after > 150 or is_mate):
            return (
                "Brilliant",
                "!!",
                "An outstanding move! Sacrifices material to create a decisive tactical advantage."
            )

        if is_best:
            return (
                "Best",
                "★",
                "The engine's top choice. Maximizes active play and maintains optimal position."
            )

        if eval_loss_cp <= 35:
            return (
                "Excellent",
                "✓",
                "A very strong alternative that preserves the core evaluation."
            )

        if eval_loss_cp <= 75:
            return (
                "Good",
                "●",
                "A solid practical move, though slightly less dynamic than the engine preference."
            )

        if eval_loss_cp <= 150:
            return (
                "Inaccuracy",
                "?!",
                "A sub-optimal move that slightly relinquishes initiative or advantage."
            )

        if eval_loss_cp <= 300:
            return (
                "Mistake",
                "?",
                "A notable error that compromises position or squanders a clear advantage."
            )

        # Greater than 300 centipawns or blundered mate
        return (
            "Blunder",
            "??",
            "A serious blunder that significantly hurts the position or loses material."
        )

    def analyze_game(self, pgn_text: str, depth: int = None, progress_callback=None) -> dict:
        """
        Perform complete move-by-move Stockfish analysis of a chess game.
        Computes evaluations, classifications, best recommendations, accuracy, and report.
        """
        game_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(game_io)
        if not game:
            raise ValueError("Invalid PGN text provided for analysis.")

        headers = dict(game.headers)
        engine = self.stockfish_service.start_engine()

        moves_analysis = []
        white_accuracies = []
        black_accuracies = []
        white_losses = []
        black_losses = []

        white_stats = {"Brilliant": 0, "Best": 0, "Excellent": 0, "Good": 0, "Inaccuracy": 0, "Mistake": 0, "Blunder": 0}
        black_stats = {"Brilliant": 0, "Best": 0, "Excellent": 0, "Good": 0, "Inaccuracy": 0, "Mistake": 0, "Blunder": 0}

        critical_moments = []
        eval_history = []

        try:
            board = game.board()
            mainline_moves = list(game.mainline_moves())
            total_moves = len(mainline_moves)

            # Evaluate initial starting position
            initial_eval = self.stockfish_service.evaluate_position(board, engine, depth=depth)
            eval_history.append({
                "move_index": 0,
                "label": "Start",
                "score_white_cp": initial_eval["score_white_cp"],
                "display_eval": initial_eval["display_eval"],
                "capped_score": max(-10.0, min(10.0, initial_eval["score_white_cp"] / 100.0)),
                "color": "white"
            })

            # Track current position evaluation before move
            current_eval = initial_eval

            for idx, move in enumerate(mainline_moves):
                player_turn = "white" if board.turn == chess.WHITE else "black"
                move_number = (idx // 2) + 1
                san_move = board.san(move)
                fen_before = board.fen()

                # Best move and eval from current position
                best_move_uci = current_eval["best_move_uci"]
                best_move_san = current_eval["best_move_san"]
                continuation = current_eval["continuation"]
                
                # Eval before move from the player's perspective
                turn_score_before = current_eval["score_turn_cp"]
                win_prob_before = self.win_probability(turn_score_before)

                # Make the move on board
                board_before = board.copy()
                board.push(move)
                fen_after = board.fen()

                # Evaluate position after the move
                next_eval = self.stockfish_service.evaluate_position(board, engine, depth=depth)
                
                # Score after move from perspective of the player who just moved
                # Since board.turn flipped, score_turn_cp in next_eval is opponent's POV.
                # So player's score is -next_eval["score_turn_cp"]
                turn_score_after = -next_eval["score_turn_cp"]
                win_prob_after = self.win_probability(turn_score_after)

                # Calculate evaluation loss (positive means player lost ground)
                eval_loss = max(0.0, turn_score_before - turn_score_after)
                
                # Calculate move accuracy
                move_acc = self.calculate_move_accuracy(win_prob_before, win_prob_after)

                # Classify move
                classification, badge, explanation = self.classify_move(
                    board_before=board_before,
                    played_move=move,
                    eval_loss_cp=eval_loss,
                    best_move_uci=best_move_uci or "",
                    turn_score_after=turn_score_after,
                    is_mate=next_eval["is_mate"]
                )

                # Update stats
                if player_turn == "white":
                    white_stats[classification] += 1
                    white_accuracies.append(move_acc)
                    white_losses.append(eval_loss)
                else:
                    black_stats[classification] += 1
                    black_accuracies.append(move_acc)
                    black_losses.append(eval_loss)

                # Check for critical moments (Mistakes, Blunders, Brilliants, or big eval swings)
                if classification in ["Blunder", "Mistake", "Brilliant"] or eval_loss >= 180:
                    critical_moments.append({
                        "move_number": move_number,
                        "player": player_turn.capitalize(),
                        "played_move": san_move,
                        "best_move": best_move_san or "N/A",
                        "classification": classification,
                        "eval_loss_pawns": round(eval_loss / 100.0, 1),
                        "explanation": explanation,
                        "eval_before": current_eval["display_eval"],
                        "eval_after": next_eval["display_eval"],
                        "fen": fen_before
                    })

                move_label = f"{move_number}. {san_move}" if player_turn == "white" else f"{move_number}... {san_move}"
                
                # Record eval history for graph
                capped_eval = max(-10.0, min(10.0, next_eval["score_white_cp"] / 100.0))
                eval_history.append({
                    "move_index": idx + 1,
                    "label": move_label,
                    "score_white_cp": next_eval["score_white_cp"],
                    "display_eval": next_eval["display_eval"],
                    "capped_score": capped_eval,
                    "color": player_turn,
                    "classification": classification
                })

                # Build move detail object
                moves_analysis.append({
                    "index": idx,
                    "move_number": move_number,
                    "turn": player_turn,
                    "san": san_move,
                    "uci": move.uci(),
                    "fen_before": fen_before,
                    "fen_after": fen_after,
                    "eval_before": current_eval["display_eval"],
                    "eval_after": next_eval["display_eval"],
                    "score_white_cp": next_eval["score_white_cp"],
                    "best_move_san": best_move_san,
                    "best_move_uci": best_move_uci,
                    "continuation": continuation,
                    "eval_loss": round(eval_loss, 1),
                    "accuracy": round(move_acc, 1),
                    "classification": classification,
                    "badge": badge,
                    "explanation": explanation
                })

                current_eval = next_eval

                if progress_callback:
                    progress_callback(idx + 1, total_moves)

        finally:
            engine.quit()

        # Overall accuracies
        avg_white_acc = round(sum(white_accuracies) / len(white_accuracies), 1) if white_accuracies else 100.0
        avg_black_acc = round(sum(black_accuracies) / len(black_accuracies), 1) if black_accuracies else 100.0

        # Average centipawn loss (ACPL)
        acpl_white = round(sum(white_losses) / len(white_losses), 1) if white_losses else 0.0
        acpl_black = round(sum(black_losses) / len(black_losses), 1) if black_losses else 0.0

        # Generate intelligent learning takeaways
        takeaways = self._generate_takeaways(
            white_stats, black_stats, avg_white_acc, avg_black_acc,
            acpl_white, acpl_black, critical_moments, headers
        )

        return {
            "headers": headers,
            "total_moves": len(moves_analysis),
            "moves": moves_analysis,
            "eval_history": eval_history,
            "report": {
                "white_accuracy": avg_white_acc,
                "black_accuracy": avg_black_acc,
                "acpl_white": acpl_white,
                "acpl_black": acpl_black,
                "white_stats": white_stats,
                "black_stats": black_stats,
                "critical_moments": critical_moments[:8],  # highlight key moments
                "key_takeaways": takeaways
            }
        }

    def _generate_takeaways(self, w_stats, b_stats, w_acc, b_acc, w_acpl, b_acpl, criticals, headers):
        """Generate structured learning advice based on engine telemetry."""
        takeaways = []

        # Accuracy comparison
        if abs(w_acc - b_acc) >= 15:
            better = "White" if w_acc > b_acc else "Black"
            worse = "Black" if w_acc > b_acc else "White"
            takeaways.append(
                f"**Accuracy Disparity**: {better} exhibited significantly higher accuracy ({max(w_acc, b_acc)}% vs {min(w_acc, b_acc)}%), dominating positional and tactical exchanges."
            )

        # Blunder diagnosis
        if w_stats["Blunder"] > 0 or b_stats["Blunder"] > 0:
            takeaways.append(
                f"**Tactical Discipline**: White committed {w_stats['Blunder']} blunder(s) and Black committed {b_stats['Blunder']} blunder(s). "
                "Reviewing undefended pieces and opponent forcing moves (checks, captures, threats) before moving will immediately cut down these swings."
            )

        # Inaccuracy accumulation
        if w_stats["Inaccuracy"] >= 4 or b_stats["Inaccuracy"] >= 4:
            takeaways.append(
                "**Positional Consolidation**: Both sides had opportunities to tighten pawn structures and improve piece coordination during middle-game transitions."
            )

        # High performance praise
        if max(w_acc, b_acc) >= 88:
            star = "White" if w_acc >= 88 else "Black"
            takeaways.append(
                f"**Master-Level Conversion**: {star} displayed impressive technical accuracy ({max(w_acc, b_acc)}%), consistently finding top engine choices."
            )

        if not takeaways:
            takeaways.append(
                "**Balanced Contest**: Both players demonstrated balanced play with low average centipawn loss and sharp defensive precision."
            )

        return takeaways
