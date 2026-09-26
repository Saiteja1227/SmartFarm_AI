# SmartFarm AI

AI-powered plant disease detection from a single leaf photo. Upload a leaf image, get an agronomist-style report with disease diagnosis, water stress level, confidence score, and actionable recommendations.

---

## Tech Stack

| Layer    | Technology                |
|----------|---------------------------|
| Backend  | Python 3.11 · Flask 3     |
| Database | MongoDB (PyMongo)         |
| AI       | Gemini Flash (via emergentintegrations) |
| Frontend | Flask/Jinja2 · Bootstrap 5 · Vanilla JS |
| Server   | Gunicorn                  |

**No Node.js, npm, React, or build tools required.**

---

## Project Structure

```
SF_AI-main/
├── run.py                  # Entry point: gunicorn run:app
├── requirements.txt
├── render.yaml             # Render deployment config
├── .env.example
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── extensions.py       # MongoDB client
│   ├── translations.py     # Server-side i18n strings
│   ├── models/
│   │   └── scan.py         # MongoDB CRUD helpers
│   ├── routes/
│   │   ├── main.py         # Page routes (Jinja2)
│   │   └── api.py          # REST API blueprint
│   ├── services/
│   │   ├── ai_service.py   # Gemini vision analysis
│   │   └── pdf_service.py  # Server-side PDF (optional)
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html      # Home / Analyzer
│   │   ├── history.html    # Scan history
│   │   └── scan_detail.html
│   └── static/
│       ├── css/app.css     # Moss & Clay theme
│       └── js/
│           ├── i18n.js     # Client-side translations
│           ├── api.js      # API fetch helpers + user ID
│           ├── app.js      # Toast, speech synthesis
│           ├── uploader.js # Drag-and-drop upload
│           ├── report.js   # Bento-grid report renderer
│           ├── history.js  # History page logic
│           ├── scan_detail.js
│           └── pdf.js      # Client-side PDF via jsPDF CDN
└── tests/
    └── test_smartfarm.py   # Integration tests
```

---

## Local Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd SF_AI-main
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   MONGO_URL=mongodb+srv://...
#   DB_NAME=smartfarm
#   EMERGENT_LLM_KEY=your_key
#   SECRET_KEY=random_secret
```

### 3. Run locally

```bash
python run.py
# or with gunicorn:
gunicorn run:app --workers 2 --timeout 120
```

Open http://localhost:5000

---

## API Reference

All endpoints require the `X-User-Id` header (8–128 chars). The browser generates and stores an anonymous UUID in `localStorage`.

| Method   | Path                   | Description                     |
|----------|------------------------|---------------------------------|
| GET      | `/api/`                | Health check                    |
| POST     | `/api/analyze`         | Analyze leaf image              |
| GET      | `/api/history`         | List user's scans (last 50)     |
| GET      | `/api/scan/<id>`       | Get full scan report            |
| DELETE   | `/api/scan/<id>`       | Delete a scan                   |
| GET      | `/api/stats`           | Dashboard counts                |
| GET      | `/api/scan/<id>/pdf`   | Download PDF (server-side)      |

### POST /api/analyze

Form-data fields:
- `image` (file, required) — JPEG, PNG, or WEBP, max 8 MB
- `crop_name` (string, optional)
- `language` (string, optional, default `en`) — `en|hi|te|ta|bn|mr|kn|gu`

---

## Features

- **Plant disease detection** — 38+ disease classes via Gemini vision
- **Water stress analysis** — Low / Moderate / High / Critical
- **Multi-language support** — English, Hindi, Telugu, Tamil, Bengali, Marathi, Kannada, Gujarati
- **Per-user isolation** — each user sees only their own scan history
- **Voice output** — Web Speech API reads the report aloud in the correct language
- **PDF export** — client-side via jsPDF (server-side fallback available)
- **Scan history** — browse, view, and delete previous analyses
- **Responsive design** — mobile and desktop

---

## Deployment on Render

1. Push to a Git repository.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Set environment variables: `MONGO_URL`, `EMERGENT_LLM_KEY`, `SECRET_KEY`, `DB_NAME`.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn run:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`

Or use the included `render.yaml` for Infrastructure-as-Code deployment.

---

## Running Tests

Integration tests require a running server and a real leaf JPEG at `/tmp/leaf.jpg`:

```bash
# Start the app first, then:
BASE_URL=http://localhost:5000 pytest tests/test_smartfarm.py -v
```
