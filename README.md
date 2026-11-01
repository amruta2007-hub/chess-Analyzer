# Chess Analyzer ♟️

A full-stack, open-source chess learning and game analysis platform prepared for dual-cloud production deployment:
- **Frontend**: Static site hosted on **Netlify**
- **Backend**: Containerized Python Flask API + **Stockfish 19** chess engine running on **Render** (via Docker & Gunicorn)

Analyze games fetched directly from **Chess.com** public profiles or uploaded **PGN** files, review tactical blunders and brilliant moves, explore alternative continuations, and view interactive game reports with win-probability accuracy metrics.

---

## 🌟 Key Features

- **Decoupled Architecture**: Fully separated static frontend and production-grade containerized Flask API with Cross-Origin Resource Sharing (CORS).
- **Chess.com Public API Integration**: Fetch the latest 20 public games for any username without requiring account login or API tokens.
- **Robust PGN Parsing**: Drag-and-drop or browse standard `.pgn` files with multi-game selection support.
- **Interactive Workspace**: Smooth Chessboard.js board with coordinate labels, auto-play, keyboard navigation (`←`, `→`, `Home`, `End`, `Space`, `F` for flip), and square move highlighting.
- **Dynamic Evaluation Bar**: Real-time vertical evaluation bar indicating White/Black centipawn advantage or forced mate distance (`M1`, `M2`, etc.).
- **Move Classification System**: Automatically identifies **Brilliant (!!)**, **Best (★)**, **Excellent (✓)**, **Good (●)**, **Inaccuracy (?!)**, **Mistake (?)**, and **Blunder (??)** based on centipawn loss and tactical sacrifice detection.
- **Engine Recommendations**: Shows Stockfish's top recommendation and continuation line (PV) for every position.
- **Comprehensive Game Report**:
  - Estimated player accuracy percentages modeled on win-probability decay.
  - Average Centipawn Loss (ACPL) for both sides.
  - Interactive Chart.js evaluation graph over the entire match.
  - Critical turning points with tactical explanations.
  - Strategic improvement takeaways.

---

## 📂 Project Structure

```
chess-analyzer/
├── Dockerfile                  # Production Docker image (Python 3.11 + Stockfish + Gunicorn)
├── render.yaml                 # Render Blueprint specification for 1-click backend deploy
├── netlify.toml                # Netlify publish directory ("frontend"), clean URLs & headers
├── inject-env.js               # Injects Netlify's API_BASE_URL into frontend at build time
├── requirements.txt            # Python dependencies (Flask, flask-cors, python-chess, gunicorn)
├── config.py                   # App configuration, CORS origins & Stockfish discovery
├── app.py                      # Flask backend API & health check routes
├── bin/
│   └── stockfish.exe           # Local Windows Stockfish UCI binary (for local dev)
├── routes/
│   ├── chesscom_routes.py      # /api/chesscom/<username>/games
│   ├── pgn_routes.py           # /api/pgn/upload
│   └── analysis_routes.py      # /api/analyze & /api/analyze/result/<id>
├── services/
│   ├── chesscom_service.py     # Chess.com public API client
│   ├── pgn_service.py          # PGN validation & python-chess extractor
│   ├── stockfish_service.py    # UCI process management & evaluation
│   └── analysis_service.py     # Move classification & accuracy modeling
├── frontend/                   # Standalone Deployable Static Site (Netlify)
│   ├── index.html              # Landing page (Chess.com fetch & PGN upload)
│   ├── games.html              # Match selection grid
│   ├── analysis.html           # Interactive analysis workspace
│   ├── report.html             # Performance review & evaluation graphs
│   ├── about.html              # Methodology & classification documentation
│   ├── css/style.css           # Modern charcoal & emerald styling
│   ├── js/
│   │   ├── env.js              # Runtime environment injection (API_BASE_URL)
│   │   ├── config.js           # API_BASE_URL resolution & getApiUrl helper
│   │   ├── main.js             # Global utilities & backend status badge
│   │   ├── games.js            # Chess.com & PGN upload handlers
│   │   ├── analysis.js         # Chessboard & live Stockfish polling
│   │   └── report.js           # Chart.js visualization & telemetry
│   ├── vendor/                 # Self-hosted Chessboard.js, Chess.js, Chart.js, jQuery
│   └── img/chesspieces/        # Self-hosted Wikipedia chess piece graphics
└── tests/
    ├── test_app.py             # 11 automated unit and integration tests
    └── test_cross_origin.py    # End-to-end cross-origin integration test
```

---

## 🚀 Complete Deployment Guide

### STEP 1: Push Code to GitHub

Open terminal in the project directory:

```powershell
cd "C:\Users\hp\.gemini\antigravity\scratch\chess-analyzer"
```

Initialize git and push to your GitHub account:

```bash
git init
git add .
git commit -m "feat: complete chess analyzer with Netlify and Render deployment configuration"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/chess-analyzer.git
git push -u origin main
```

---

### STEP 2: Deploy the Backend to Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository (`chess-analyzer`).
4. Configure the Web Service settings:
   - **Name**: `chess-analyzer-backend` (or your preferred name)
   - **Region**: Choose the closest region (e.g., `Frankfurt`, `Oregon`, `Ohio`)
   - **Language / Environment**: Select **Docker**
   - **Dockerfile Path**: `Dockerfile` (or leave default `./Dockerfile`)
   - **Instance Type**: **Free**
5. Under **Environment Variables**, add:
   | Key | Value | Description |
   |---|---|---|
   | `CORS_ORIGINS` | `*` *(or your Netlify URL once deployed)* | Allows cross-origin API calls |
   | `SECRET_KEY` | *(Click generate or enter random string)* | Flask session security |
   | `STOCKFISH_DEPTH` | `12` | Search depth per position |
   | `STOCKFISH_TIME_LIMIT` | `0.12` | Time budget per move (seconds) |
6. Click **Deploy Web Service**.
7. Wait 2-3 minutes for the Docker image to build. Once deployed, note down your Render service URL:
   `https://chess-analyzer-backend.onrender.com`
8. Verify backend health by visiting in your browser:
   `https://chess-analyzer-backend.onrender.com/api/health`
   You should see:
   ```json
   {
     "service": "Chess Analyzer API",
     "status": "healthy",
     "stockfish": {
       "available": true,
       "instructions": "Stockfish engine ready.",
       "path": "/usr/games/stockfish"
     }
   }
   ```

---

### STEP 3: Deploy the Frontend to Netlify

1. Log in to your [Netlify Dashboard](https://app.netlify.com/).
2. Click **Add new site** > **Import an existing project**.
3. Select **GitHub** and authorize access to your `chess-analyzer` repository.
4. Netlify will automatically detect `netlify.toml` with the following build settings:
   - **Base directory**: *(Leave empty)*
   - **Build command**: `node inject-env.js`
   - **Publish directory**: `frontend`
5. Click **Add environment variables** (or go to **Site configuration > Environment variables**) and add:
   | Key | Value | Description |
   |---|---|---|
   | `API_BASE_URL` | `https://chess-analyzer-backend.onrender.com` | Your live Render backend URL from Step 2 |
6. Click **Deploy site**.
7. Netlify will build and deploy your site in ~30 seconds, giving you a live URL like:
   `https://chess-analyzer-app.netlify.app`

---

### STEP 4: Lock Down CORS (Recommended for Production)

Once your Netlify site is live:
1. Copy your Netlify site domain: `https://chess-analyzer-app.netlify.app`.
2. Go to your Render Dashboard > **chess-analyzer-backend** > **Environment**.
3. Update the `CORS_ORIGINS` variable:
   ```
   CORS_ORIGINS = https://chess-analyzer-app.netlify.app
   ```
4. Click **Save Changes** (Render will redeploy with tightened CORS permissions).

---

## 🧪 Testing Locally

### Running Backend Locally (Port 5000):
```powershell
python app.py
```
Backend health check: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

### Running Static Frontend Locally (Port 8888):
```powershell
python -m http.server 8888 --directory frontend
```
Open [http://127.0.0.1:8888](http://127.0.0.1:8888) in your browser.

### In-Browser Backend Configuration:
If you need to change the backend URL at any time in the frontend, click the **🟢 API Connected** badge in the top navigation bar to open the **Backend API Settings** modal and enter any local or Render URL.

### Running Automated Test Suite:
```powershell
python -m unittest tests/test_app.py
python tests/test_cross_origin.py
```

---

## 📜 Technical Details

- **Containerization**: Standard `python:3.11-slim` image installing official Debian `stockfish` package via `apt-get` and setting `STOCKFISH_PATH=/usr/games/stockfish`.
- **WSGI Server**: Gunicorn running with 2 worker processes and 4 threads to handle concurrent requests and background analysis jobs without blocking.
- **Accuracy Model**: Logistical win-probability curve modeled after modern engine telemetry:
  $$W(cp) = \frac{100}{1 + e^{-0.00368208 \times cp}}$$
  $$\text{Accuracy} = 103.1668 \times e^{-0.04354 \times \Delta W} - 3.1669$$
- **CORS Handling**: Handled via `Flask-CORS` on all `/api/*` routes supporting preflight `OPTIONS` requests and cross-origin `multipart/form-data` uploads.
