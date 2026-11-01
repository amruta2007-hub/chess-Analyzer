import requests
import time
import io

FRONTEND_ORIGIN = "http://127.0.0.1:8888"
BACKEND_URL = "http://127.0.0.1:5000"

def test_cross_origin():
    print("=== 1. Testing Health & CORS Preflight ===")
    r = requests.options(
        f"{BACKEND_URL}/api/analyze",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )
    assert r.status_code == 200, f"Preflight failed: {r.status_code}"
    assert "Access-Control-Allow-Origin" in r.headers
    print("Preflight OPTIONS successful! CORS origin allowed:", r.headers.get("Access-Control-Allow-Origin"))

    print("\n=== 2. Testing Chess.com Games Lookup from Frontend Origin ===")
    r = requests.get(f"{BACKEND_URL}/api/chesscom/Hikaru/games", headers={"Origin": FRONTEND_ORIGIN})
    assert r.status_code == 200, f"Chess.com games failed: {r.status_code}"
    data = r.json()
    assert data["success"] and len(data["games"]) > 0
    print(f"Fetched {len(data['games'])} games for {data['player']['username']}. CORS header: {r.headers.get('Access-Control-Allow-Origin')}")

    print("\n=== 3. Testing Multipart PGN Upload from Frontend Origin ===")
    sample_pgn = b"1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"
    files = {"file": ("game.pgn", io.BytesIO(sample_pgn), "application/x-chess-pgn")}
    r = requests.post(f"{BACKEND_URL}/api/pgn/upload", files=files, headers={"Origin": FRONTEND_ORIGIN})
    assert r.status_code == 200, f"PGN upload failed: {r.status_code}"
    upload_data = r.json()
    assert upload_data["success"]
    print("PGN uploaded and parsed successfully across origins! Games count:", upload_data["games_count"])

    print("\n=== 4. Testing Async Stockfish Analysis Across Origins ===")
    r = requests.post(
        f"{BACKEND_URL}/api/analyze",
        json={"pgn": sample_pgn.decode("utf-8"), "depth": 8},
        headers={"Origin": FRONTEND_ORIGIN}
    )
    assert r.status_code == 202, f"Analyze start failed: {r.status_code}"
    analysis_id = r.json()["analysis_id"]
    print("Analysis initiated with ID:", analysis_id)

    print("Polling analysis progress...")
    completed = False
    for _ in range(20):
        poll_resp = requests.get(
            f"{BACKEND_URL}/api/analyze/result/{analysis_id}",
            headers={"Origin": FRONTEND_ORIGIN}
        )
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        if poll_data["status"] == "completed":
            completed = True
            print("Analysis complete!")
            print("White accuracy:", poll_data["result"]["report"]["white_accuracy"])
            print("Black accuracy:", poll_data["result"]["report"]["black_accuracy"])
            print("White blunders:", poll_data["result"]["report"]["white_stats"]["Blunder"])
            print("Black blunders:", poll_data["result"]["report"]["black_stats"]["Blunder"])
            break
        time.sleep(0.5)

    assert completed, "Analysis did not complete"
    print("\n>>> ALL CROSS-ORIGIN FRONTEND/BACKEND TESTS PASSED 100%! <<<")

if __name__ == "__main__":
    test_cross_origin()
