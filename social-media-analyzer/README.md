# Social Media Content Analyzer

Upload a PDF or a scanned image of a social media post. The app extracts the
text (PDF parsing or OCR) and returns a quick rule-based engagement analysis
with suggestions.

**Stack:** Single Flask app (Python) serving a vanilla HTML/CSS/JS frontend —
one process, one repo, no build step, no API keys required.



## Features

- Drag-and-drop **or** file-picker upload for PDFs and images
- **PDF parsing** with [pdfplumber](https://github.com/jsvine/pdfplumber), preserving line/paragraph layout;
  automatically falls back to OCR for pages that have no text layer (e.g. scanned PDFs)
- **OCR** for image uploads (PNG/JPG/WEBP/BMP/TIFF) via [Tesseract](https://github.com/tesseract-ocr/tesseract)
- Rule-based **engagement suggestions**: word count, hashtag/mention/emoji counts,
  question detection, call-to-action detection, sentence length
- Loading state while a file is processing, and clear error messages for
  unsupported file types, oversized files, or corrupted/unreadable files

## Project structure

```
social-media-analyzer/
├── app.py                # Flask app: routes, PDF/OCR extraction, analysis logic
├── templates/index.html  # Single-page frontend
├── static/style.css
├── static/script.js      # Drag-and-drop, fetch call, rendering
├── requirements.txt
├── Dockerfile            # Bundles Tesseract so OCR works in any container host
└── test_files/           # Sample PDF/image used for manual testing
```

## Run locally

Requires Python 3.9+ and the Tesseract OCR binary installed on your system
(`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Debian/Ubuntu).

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Deploy

The only non-Python dependency is the Tesseract binary, so the simplest path
is the included **Dockerfile** — it works as-is on Render, Railway, Fly.io, or
any container host:

```bash
docker build -t sm-analyzer .
docker run -p 5000:5000 sm-analyzer
```

On a host that lets you install system packages directly (e.g. Railway's
Nixpacks, a VM, PythonAnywhere), you can skip Docker and just run
`pip install -r requirements.txt` + ensure `tesseract-ocr` is installed, then
start with `gunicorn app:app`.

## Approach (~200 words)

I optimized for a single, easy-to-run service rather than a split
frontend/backend, since the assignment rewards a working, well-documented
tool over architectural complexity. Flask serves both the static UI and a
single JSON endpoint (`/api/analyze`), so there's one process to run and
deploy.

For extraction, `pdfplumber` handles native PDF text with layout preservation;
if a page has no text layer (a scanned PDF), the app rasterizes that page and
runs Tesseract OCR on it automatically, so both "real" and scanned PDFs work
through the same code path. Standalone images go straight to Tesseract.

For the "engagement improvement" piece, I used transparent, rule-based
heuristics (length, hashtags, mentions, emojis, question/CTA presence)
instead of calling an external LLM. This keeps the app free to run, fast,
deterministic, and dependency-free on API keys — appropriate given the
8-hour time box — while still giving genuinely useful, explainable
suggestions.

The frontend is deliberately dependency-free (no framework/build step):
drag-and-drop plus a file-picker fallback, a loading spinner during
requests, and a dedicated error state for unsupported types, oversized
files, or unreadable/corrupted uploads.

## Notes / possible extensions

- Swap the rule-based analyzer for an LLM call (e.g. Anthropic/OpenAI free
  tier) for richer, tone-aware suggestions
- Add multi-file batch upload
- Persist analysis history per user
