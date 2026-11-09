"""
Cloud Run service: reads a text file from a PRIVATE Cloud Storage bucket
and shows its name + content in the browser.

Flow:  Browser  ->  Cloud Run (this app)  ->  Cloud Storage (message.txt)

Configuration (set at deploy time, never hard-coded):
  BUCKET_NAME  - the private bucket to read from (required)
  OBJECT_NAME  - path of the file inside the bucket (default: message.txt)

Authentication: no keys in code. On Cloud Run the client library uses the
service's own identity (its service account), which must have
roles/storage.objectViewer on the bucket.
"""

import html
import os

from flask import Flask
from google.api_core import exceptions as gexc
from google.cloud import storage

app = Flask(__name__)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "").strip()
OBJECT_NAME = os.environ.get("OBJECT_NAME", "message.txt").strip()

# One client per container instance. It holds credentials only, not file content,
# so the file itself is still fetched fresh on every request.
_client = storage.Client() if BUCKET_NAME else None

PAGE = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, Arial, sans-serif; background:#f6f8fb; color:#1b2b44;
         max-width: 720px; margin: 48px auto; padding: 0 16px; }}
  .card {{ background:#fff; border:1px solid #d6e2f0; border-radius:12px; padding:24px; }}
  .file {{ font-family: ui-monospace, Consolas, monospace; color:#4a6080; font-size:14px; }}
  .content {{ font-size: 28px; font-weight: 700; white-space: pre-wrap; margin-top: 12px; }}
  .error {{ border-color:#e7b4b4; background:#fff6f6; }}
  .error h1 {{ color:#a12b2b; font-size: 22px; margin: 0 0 8px; }}
  button {{ margin-top:16px; padding:8px 16px; border-radius:8px; border:1px solid #9bb3d1;
           background:#fff; cursor:pointer; font-size:15px; }}
</style>
</head>
<body>
  <div class="card {extra_class}">
    {body}
  </div>
</body>
</html>"""


def render_ok(object_name: str, text: str) -> str:
    body = (
        f'<div class="file">קובץ: gs://{html.escape(BUCKET_NAME)}/{html.escape(object_name)}</div>'
        f'<div class="content">{html.escape(text)}</div>'
    )
    return PAGE.format(title=html.escape(object_name), extra_class="", body=body)


def render_error(headline: str, detail: str) -> str:
    body = (
        f"<h1>{html.escape(headline)}</h1>"
        f"<div>{html.escape(detail)}</div>"
        f'<div class="file">מקור: gs://{html.escape(BUCKET_NAME or "?")}/{html.escape(OBJECT_NAME)}</div>'
        '<button onclick="location.reload()">נסו שוב</button>'
    )
    return PAGE.format(title="שגיאה בקריאת הקובץ", extra_class="error", body=body)


def no_cache(resp_tuple):
    """Stop the browser / proxies from caching, so a refresh always shows the current file."""
    body, status = resp_tuple
    return body, status, {"Cache-Control": "no-store", "Content-Type": "text/html; charset=utf-8"}


@app.get("/")
def index():
    # Step 1: configuration check - a missing setting stays missing, we report it.
    if not BUCKET_NAME:
        return no_cache((render_error(
            "השירות לא הוגדר",
            "חסר משתנה הסביבה BUCKET_NAME. יש לפנות למי שמפעיל את השירות.",
        ), 500))

    # Step 2: read the file from Cloud Storage on EVERY request (no caching).
    try:
        blob = _client.bucket(BUCKET_NAME).blob(OBJECT_NAME)
        data = blob.download_as_bytes()
    except gexc.NotFound:
        return no_cache((render_error(
            "הקובץ לא נמצא",
            f"הקובץ {OBJECT_NAME} לא קיים כרגע באחסון. ייתכן שהוא מוחלף ממש עכשיו - נסו לרענן בעוד רגע.",
        ), 404))
    except gexc.Forbidden:
        return no_cache((render_error(
            "אין הרשאה לקרוא את הקובץ",
            "לזהות של השירות אין הרשאת קריאה ל-bucket. יש לפנות למי שמפעיל את השירות.",
        ), 500))
    except Exception as e:  # network / unexpected - log it, show a generic message
        app.logger.exception("Failed to read gs://%s/%s", BUCKET_NAME, OBJECT_NAME)
        return no_cache((render_error(
            "שגיאה זמנית בקריאת הקובץ",
            f"לא הצלחנו לקרוא את הקובץ ({type(e).__name__}). נסו לרענן בעוד רגע.",
        ), 502))

    # Step 3: decode as UTF-8 text; a non-text / corrupt file gets its own message.
    try:
        # utf-8-sig also strips a BOM, which Windows tools sometimes add to .txt files
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return no_cache((render_error(
            "פורמט קובץ לא נתמך",
            "הקובץ קיים אך אינו טקסט בקידוד UTF-8. יש להעלות קובץ טקסט תקין.",
        ), 415))

    return no_cache((render_ok(OBJECT_NAME, text), 200))


@app.get("/healthz")
def healthz():
    # Liveness check that does NOT touch Cloud Storage.
    return "ok", 200


if __name__ == "__main__":
    # Local run only. On Cloud Run, gunicorn (see Procfile) serves the app.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=False)
