"""
Social Media Content Analyzer
------------------------------
A minimal Flask app that:
  1. Accepts a PDF or image upload (drag-and-drop or file picker, handled by the frontend)
  2. Extracts text (PDF parsing via pdfplumber, OCR via pytesseract for images)
  3. Runs a lightweight rule-based analysis and returns engagement suggestions

Kept intentionally simple: one Flask process serves both the static frontend
and the JSON API, so there is a single service to run and deploy.
"""

import io
import os
import re

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from PIL import Image
import pdfplumber
import pytesseract

app = Flask(__name__)
CORS(app)

ALLOWED_PDF = {"pdf"}
ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}
MAX_FILE_SIZE_MB = 20

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024


def get_extension(filename):
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def extract_text_from_pdf(file_stream):
    """
    Extract text page-by-page with pdfplumber, preserving paragraph/line
    structure as closely as a plain-text extraction reasonably can.
    Falls back to OCR-per-page if a page has no extractable text
    (e.g. a scanned/image-only PDF).
    """
    pages_text = []
    with pdfplumber.open(file_stream) as pdf:
        if len(pdf.pages) == 0:
            raise ValueError("The PDF has no pages.")

        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=True) or ""
            text = text.strip()

            if not text:
                # Scanned page with no text layer -> OCR it as an image
                try:
                    pil_image = page.to_image(resolution=200).original
                    text = pytesseract.image_to_string(pil_image).strip()
                except Exception:
                    text = ""

            pages_text.append(
                {
                    "page": page_number,
                    "text": text if text else "[No extractable text on this page]",
                }
            )

    full_text = "\n\n".join(p["text"] for p in pages_text)
    return full_text, pages_text


def extract_text_from_image(file_stream):
    """Run OCR on a single uploaded image."""
    image = Image.open(file_stream)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image).strip()
    return text


EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

CTA_KEYWORDS = [
    "click", "follow", "subscribe", "share", "comment", "link in bio",
    "sign up", "buy now", "learn more", "dm us", "tag a friend",
    "swipe up", "shop now", "download", "join",
]


def analyze_content(text):
    """
    Simple, transparent rule-based engagement analysis.
    No external AI/ML calls -> no API keys, no extra latency, easy to reason about.
    """
    clean_text = text.strip()
    if not clean_text:
        return {
            "word_count": 0,
            "hashtag_count": 0,
            "mention_count": 0,
            "emoji_count": 0,
            "has_question": False,
            "has_call_to_action": False,
            "suggestions": [
                "No text could be extracted, so no engagement analysis is available."
            ],
        }

    words = clean_text.split()
    word_count = len(words)

    hashtags = re.findall(r"#\w+", clean_text)
    mentions = re.findall(r"@\w+", clean_text)
    emojis = EMOJI_PATTERN.findall(clean_text)
    emoji_count = sum(len(e) for e in emojis)

    has_question = "?" in clean_text
    lowered = clean_text.lower()
    has_cta = any(keyword in lowered for keyword in CTA_KEYWORDS)

    sentences = [s for s in re.split(r"[.!?]+", clean_text) if s.strip()]
    avg_sentence_len = (
        sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
    )

    suggestions = []

    if word_count > 80:
        suggestions.append(
            "This post is fairly long. Consider trimming it down for platforms "
            "like X/Twitter or Instagram captions, where shorter posts tend to "
            "get read (and engaged with) more fully."
        )
    elif word_count < 5:
        suggestions.append(
            "The post is very short. Adding a bit more context or a hook could "
            "help it stand out in a feed."
        )

    if len(hashtags) == 0:
        suggestions.append(
            "No hashtags detected. Adding 2-5 relevant hashtags can meaningfully "
            "increase discoverability."
        )
    elif len(hashtags) > 10:
        suggestions.append(
            "There are quite a few hashtags. More than ~10 can look spammy; "
            "consider narrowing to the most relevant ones."
        )

    if not has_question:
        suggestions.append(
            "Consider asking a question. Posts that invite a reply tend to get "
            "more comments."
        )

    if emoji_count == 0:
        suggestions.append(
            "No emojis detected. A well-placed emoji or two can make posts feel "
            "more approachable and draw the eye in a busy feed."
        )

    if not has_cta:
        suggestions.append(
            "No clear call-to-action found (e.g. 'comment below', 'share this', "
            "'follow for more'). A direct CTA can lift engagement."
        )

    if avg_sentence_len > 25:
        suggestions.append(
            "Sentences are quite long on average. Shorter, punchier sentences "
            "are generally easier to skim on social media."
        )

    if not suggestions:
        suggestions.append(
            "This post already hits the basics well: good length, hashtags, "
            "and a call-to-action. Nice work!"
        )

    return {
        "word_count": word_count,
        "hashtag_count": len(hashtags),
        "mention_count": len(mentions),
        "emoji_count": emoji_count,
        "has_question": has_question,
        "has_call_to_action": has_cta,
        "suggestions": suggestions,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file was uploaded."}), 400

    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"success": False, "error": "No file was selected."}), 400

    ext = get_extension(uploaded_file.filename)

    try:
        if ext in ALLOWED_PDF:
            stream = io.BytesIO(uploaded_file.read())
            full_text, pages = extract_text_from_pdf(stream)
            file_type = "pdf"
        elif ext in ALLOWED_IMAGE:
            stream = io.BytesIO(uploaded_file.read())
            full_text = extract_text_from_image(stream)
            pages = None
            file_type = "image"
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Unsupported file type '.{ext}'. "
                        f"Please upload a PDF or an image "
                        f"({', '.join(sorted(ALLOWED_IMAGE))}).",
                    }
                ),
                400,
            )
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a clean message
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Could not process this file. It may be corrupted, "
                    f"password-protected, or in an unsupported format. "
                    f"({str(exc)[:200]})",
                }
            ),
            422,
        )

    analysis = analyze_content(full_text)

    response = {
        "success": True,
        "file_type": file_type,
        "filename": uploaded_file.filename,
        "extracted_text": full_text if full_text.strip() else "",
        "analysis": analysis,
    }
    if pages is not None:
        response["pages"] = pages

    return jsonify(response)


@app.errorhandler(413)
def too_large(_error):
    return (
        jsonify(
            {
                "success": False,
                "error": f"File is too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
            }
        ),
        413,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
