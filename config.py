"""
QC-Check 02 設定ファイル
Configuration for the QC inspection capture station.

Note: Python 3.15a2 — using pure-Python approach (no numpy/opencv).
Camera capture is handled client-side via WebRTC / getUserMedia.
"""
import os

# ── データディレクトリ ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OK_DIR = os.path.join(DATA_DIR, "ok")
NG_DIR = os.path.join(DATA_DIR, "ng")
UNLABELED_DIR = os.path.join(DATA_DIR, "unlabeled")
METADATA_CSV = os.path.join(DATA_DIR, "metadata.csv")

# ── 画像設定 ──
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
PROCESS_WIDTH = 640
PROCESS_HEIGHT = 480
JPEG_QUALITY = 95

# ── Flask 設定 ──
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# ── Database 設定 ──
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATA_DIR, 'qc_check.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# データフォルダを自動作成
for d in [DATA_DIR, OK_DIR, NG_DIR, UNLABELED_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Cloud Vision API ──
# Set your API keys here or use environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

