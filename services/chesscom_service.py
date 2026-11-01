import re
import datetime
import requests
from config import Config

class ChesscomError(Exception):
    """Base exception for Chess.com API interactions."""
    pass

class UserNotFoundError(ChesscomError):
    """Raised when the specified username does not exist on Chess.com."""
    pass

class RateLimitError(ChesscomError):
    """Raised when Chess.com returns HTTP 429 Rate Limited."""
    pass

class ChesscomService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": Config.CHESSCOM_USER_AGENT,
            "Accept": "application/json"
        })
        self.timeout = Config.CHESSCOM_TIMEOUT

    @staticmethod
    def validate_username(username: str) -> str:
        """
        Validate and sanitize Chess.com username format.
        Must be 3-35 alphanumeric chars, hyphens, or underscores.
        """
        if not username or not isinstance(username, str):
            raise ValueError("Username cannot be empty.")
        
        cleaned = username.strip().lower()
        if not re.match(r"^[a-z0-9_-]{3,35}$", cleaned):
            raise ValueError(
                "Invalid username format. Usernames must be 3-35 characters containing only letters, numbers, underscores, or hyphens."
            )
        return cleaned

    def get_player_profile(self, username: str) -> dict:
        """
        Fetch public profile for a Chess.com player.
        """
        valid_username = self.validate_username(username)
        url = f"{Config.CHESSCOM_API_BASE}/player/{valid_username}"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                raise UserNotFoundError(f"Player '{username}' was not found on Chess.com.")
            elif resp.status_code == 429:
                raise RateLimitError("Chess.com API rate limit reached. Please wait a moment before trying again.")
            resp.raise_for_status()

            data = resp.json()
            return {
                "username": data.get("username", valid_username),
                "name": data.get("name", ""),
                "avatar": data.get("avatar", ""),
                "title": data.get("title", ""),
                "country": data.get("country", ""),
                "url": data.get("url", f"https://www.chess.com/member/{valid_username}"),
                "status": data.get("status", "basic")
            }
        except requests.Timeout:
            raise ChesscomError("Chess.com server timed out. Please check your internet connection or try again.")
        except requests.RequestException as e:
            if not isinstance(e, ChesscomError):
                raise ChesscomError(f"Network error communicating with Chess.com: {str(e)}")
            raise

    def get_latest_games(self, username: str, limit: int = 20) -> dict:
        """
        Fetch the player profile and latest games (default 20), sorted by end time descending.
        Processes monthly archives from newest to oldest.
        """
        valid_username = self.validate_username(username)
        profile = self.get_player_profile(valid_username)

        archives_url = f"{Config.CHESSCOM_API_BASE}/player/{valid_username}/games/archives"
        try:
            resp = self.session.get(archives_url, timeout=self.timeout)
            if resp.status_code == 404:
                return {"player": profile, "games": []}
            elif resp.status_code == 429:
                raise RateLimitError("Chess.com API rate limit reached. Please wait a few moments.")
            resp.raise_for_status()

            archives_data = resp.json()
            archive_urls = archives_data.get("archives", [])
        except requests.Timeout:
            raise ChesscomError("Request timed out while fetching monthly archives.")
        except requests.RequestException as e:
            raise ChesscomError(f"Failed to fetch game archives: {str(e)}")

        if not archive_urls:
            return {"player": profile, "games": []}

        # Process monthly archives from newest to oldest
        collected_games = []
        reversed_archives = list(reversed(archive_urls))

        for month_url in reversed_archives:
            try:
                m_resp = self.session.get(month_url, timeout=self.timeout)
                if m_resp.status_code == 200:
                    month_data = m_resp.json()
                    month_games = month_data.get("games", [])

                    # Filter for standard chess and valid PGN
                    for g in month_games:
                        if g.get("rules", "chess") != "chess":
                            continue  # skip chess960, bughouse, etc.
                        
                        formatted = self._format_game(g, valid_username)
                        if formatted:
                            collected_games.append(formatted)

                    if len(collected_games) >= limit * 2:
                        break
            except Exception:
                # Continue trying previous month if one fails
                continue

        # Sort strictly by end_time descending
        collected_games.sort(key=lambda x: x.get("end_time", 0), reverse=True)
        selected_games = collected_games[:limit]

        return {
            "player": profile,
            "games": selected_games,
            "total_fetched": len(selected_games)
        }

    def _format_game(self, raw_game: dict, current_username: str) -> dict:
        """Format raw Chess.com game object into clean structured dictionary."""
        white_data = raw_game.get("white", {})
        black_data = raw_game.get("black", {})

        white_user = white_data.get("username", "Unknown")
        black_user = black_data.get("username", "Unknown")

        is_user_white = white_user.lower() == current_username.lower()
        user_color = "white" if is_user_white else "black"
        opponent_color = "black" if is_user_white else "white"

        user_data = white_data if is_user_white else black_data
        opp_data = black_data if is_user_white else white_data

        user_rating = user_data.get("rating", 0)
        opp_rating = opp_data.get("rating", 0)
        user_result = user_data.get("result", "unknown")
        opp_result = opp_data.get("result", "unknown")

        end_time = raw_game.get("end_time", 0)
        date_str = ""
        if end_time:
            try:
                date_str = datetime.datetime.fromtimestamp(end_time, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                date_str = "Recent"

        # Determine readable result
        outcome = "Draw"
        if user_result == "win":
            outcome = "Win"
        elif opp_result == "win":
            outcome = "Loss"
        elif user_result in ["checkmated", "resigned", "timeout", "abandoned"]:
            outcome = "Loss"

        pgn_text = raw_game.get("pgn", "")

        return {
            "id": raw_game.get("uuid") or raw_game.get("url", "").split("/")[-1],
            "url": raw_game.get("url", ""),
            "end_time": end_time,
            "date": date_str,
            "time_control": raw_game.get("time_control", ""),
            "time_class": raw_game.get("time_class", "Standard"),
            "rules": raw_game.get("rules", "chess"),
            "white": {
                "username": white_user,
                "rating": white_data.get("rating", "?"),
                "result": white_data.get("result", "")
            },
            "black": {
                "username": black_user,
                "rating": black_data.get("rating", "?"),
                "result": black_data.get("result", "")
            },
            "user_color": user_color,
            "opponent_username": opp_data.get("username", "Opponent"),
            "opponent_rating": opp_rating,
            "user_rating": user_rating,
            "outcome": outcome,
            "pgn": pgn_text
        }
