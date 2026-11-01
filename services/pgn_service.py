import io
import os
import chess
import chess.pgn
from werkzeug.utils import secure_filename
from config import Config

class PGNError(Exception):
    """Base exception for PGN parsing errors."""
    pass

class PGNService:
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file has an allowed PGN extension."""
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_and_read_content(file_storage) -> str:
        """
        Validate file size and extract text content safely with encoding fallbacks.
        Never executes any uploaded data.
        """
        if not file_storage or not file_storage.filename:
            raise PGNError("No file selected or empty file uploaded.")

        if not PGNService.allowed_file(file_storage.filename):
            raise PGNError("Invalid file type. Only standard chess .pgn files are supported.")

        # Read content bytes
        content_bytes = file_storage.read()
        if len(content_bytes) == 0:
            raise PGNError("The uploaded file is empty.")

        if len(content_bytes) > Config.MAX_CONTENT_LENGTH:
            raise PGNError("File size exceeds the 5MB upload limit.")

        # Decode with fallback encodings
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        raise PGNError("Could not decode file content. Please ensure the PGN is a valid text file.")

    @staticmethod
    def parse_pgn_text(pgn_text: str) -> list:
        """
        Parse one or multiple PGN games from raw text.
        Extracts metadata, moves, and board states.
        """
        if not pgn_text or not pgn_text.strip():
            raise PGNError("Empty PGN text provided.")

        pgn_io = io.StringIO(pgn_text)
        games_list = []
        game_index = 0

        while True:
            try:
                game = chess.pgn.read_game(pgn_io)
            except Exception as e:
                # If we already parsed at least one game, stop gracefully
                if games_list:
                    break
                raise PGNError(f"Failed to parse PGN syntax: {str(e)}")

            if game is None:
                break

            headers = dict(game.headers)
            white_name = headers.get("White", "Unknown White")
            black_name = headers.get("Black", "Unknown Black")
            white_elo = headers.get("WhiteElo", headers.get("WhiteRating", "?"))
            black_elo = headers.get("BlackElo", headers.get("BlackRating", "?"))
            date = headers.get("Date", "????.??.??")
            result = headers.get("Result", "*")
            event = headers.get("Event", "Casual Game")
            site = headers.get("Site", "")
            time_control = headers.get("TimeControl", "")

            # Extract moves and positions
            moves_data = []
            board = game.board()
            
            for move in game.mainline_moves():
                san = board.san(move)
                uci = move.uci()
                board.push(move)
                moves_data.append({
                    "san": san,
                    "uci": uci,
                    "fen": board.fen()
                })

            # Reconstruct single-game PGN string
            exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
            single_pgn = game.accept(exporter)

            game_data = {
                "index": game_index,
                "white": {
                    "username": white_name,
                    "rating": white_elo
                },
                "black": {
                    "username": black_name,
                    "rating": black_elo
                },
                "date": date,
                "result": result,
                "event": event,
                "site": site,
                "time_control": time_control,
                "moves_count": len(moves_data),
                "moves": moves_data,
                "pgn": single_pgn
            }

            games_list.append(game_data)
            game_index += 1

        if not games_list:
            raise PGNError("No valid chess games could be identified in the uploaded PGN.")

        return games_list
