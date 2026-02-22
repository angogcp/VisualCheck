"""
QC-Check 02 — メインアプリケーション
Flask web application for cable inspection capture station.

Architecture: Camera capture is handled client-side via WebRTC/getUserMedia.
Images are sent as base64 data URLs from the browser canvas.
This avoids numpy/opencv dependency issues with Python 3.15.
"""
import os

import base64
from flask import (
    Flask, render_template, request, jsonify,
    send_file, Response,
)
import threading
from modules.ai_engine import ai_engine, DATA_ROOT

# Training status lock/flag
training_active = False
training_lock = threading.Lock()

import config
from modules.storage import (
    save_image_from_base64,
    relabel_image,
    delete_image,
    get_recent_images,
    get_filtered_images,
    get_statistics,
    get_daily_statistics,
    export_csv_content,
    init_db
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

# Initialize the SQLite database and migrate old CSV data if needed
init_db(app)


# ── ページルート ──

@app.route("/")
def index():
    """メイン画面（キャプチャ）"""
    mode = request.args.get("mode", "admin")
    stats = get_statistics()
    recent = get_recent_images(12)
    return render_template(
        "index.html",
        stats=stats,
        recent=recent,
        active_page="capture",
        mode=mode,
    )


@app.route("/gallery-page")
def gallery_page():
    """ギャラリー画面"""
    stats = get_statistics()
    return render_template(
        "gallery.html",
        stats=stats,
        active_page="gallery",
    )


@app.route("/reports")
def reports_page():
    """レポート画面"""
    stats = get_statistics()
    daily = get_daily_statistics(30)
    return render_template(
        "reports.html",
        stats=stats,
        daily=daily,
        active_page="reports",
    )


# ── API エンドポイント ──

@app.route("/capture", methods=["POST"])
def capture():
    """ブラウザから送られた画像を unlabeled に保存"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "データがありません"}), 400

    image_data = data.get("image", "")
    cable_id = data.get("cable_id", "")

    if not image_data:
        return jsonify({"success": False, "error": "画像データがありません"}), 400

    try:
        filepath, filename = save_image_from_base64(
            image_data, label="unlabeled", cable_id=cable_id
        )
        return jsonify({
            "success": True,
            "filepath": filepath,
            "filename": filename,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/label", methods=["POST"])
def label():
    """画像のラベルを変更する（OK / NG）"""
    data = request.get_json()
    filepath = data.get("filepath", "")
    new_label = data.get("label", "")

    if new_label not in ("ok", "ng", "unlabeled"):
        return jsonify({"success": False, "error": "無効なラベルです"}), 400

    if not filepath or not os.path.exists(filepath):
        return jsonify({"success": False, "error": "ファイルが見つかりません"}), 404

    new_path = relabel_image(filepath, new_label)
    return jsonify({
        "success": True,
        "new_filepath": new_path,
        "label": new_label,
    })


@app.route("/gallery")
def gallery():
    """フィルタ付き画像一覧を JSON で返す"""
    label_filter = request.args.get("label", "")
    cable_id = request.args.get("cable_id", "")
    n = request.args.get("n", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    # 後方互換: n パラメータのみ指定の場合は get_recent_images を使う
    if not label_filter and not cable_id and offset == 0:
        recent = get_recent_images(n)
        return jsonify(recent)

    result = get_filtered_images(
        label=label_filter,
        cable_id=cable_id,
        limit=n,
        offset=offset,
    )
    return jsonify(result)


@app.route("/image", methods=["DELETE"])
def delete_image_route():
    """画像を削除する"""
    data = request.get_json()
    filepath = data.get("filepath", "")

    if not filepath:
        return jsonify({"success": False, "error": "パスが指定されていません"}), 400

    abs_path = os.path.abspath(filepath)
    data_abs = os.path.abspath(config.DATA_DIR)

    if not abs_path.startswith(data_abs):
        return jsonify({"success": False, "error": "アクセス拒否"}), 403

    if not os.path.exists(abs_path):
        return jsonify({"success": False, "error": "ファイルが見つかりません"}), 404

    delete_image(abs_path)
    return jsonify({"success": True})


@app.route("/stats")
def stats():
    """統計情報を JSON で返す"""
    return jsonify(get_statistics())


@app.route("/api/daily-stats")
def daily_stats():
    """日別統計を JSON で返す"""
    days = request.args.get("days", 30, type=int)
    return jsonify(get_daily_statistics(days))


@app.route("/export")
def export_csv():
    """メタデータCSVをダウンロードする"""
    content = export_csv_content()
    if not content:
        return "データがありません", 404
    return Response(
        content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=qc_check_metadata.csv",
        },
    )


@app.route("/image")
def serve_image():
    """保存された画像を配信する（クエリパラメータでパスを受け取る）"""
    filepath = request.args.get("path", "")
    if not filepath:
        return "パスが指定されていません", 400

    abs_path = os.path.abspath(filepath)
    data_abs = os.path.abspath(config.DATA_DIR)

    # セキュリティチェック: data ディレクトリ内のみ許可
    if not abs_path.startswith(data_abs):
        return "アクセス拒否", 403
    if not os.path.exists(abs_path):
        return "ファイルが見つかりません", 404

    # MIME タイプを拡張子から判定
    ext = os.path.splitext(abs_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mimetype = mime_map.get(ext, "application/octet-stream")

    return send_file(abs_path, mimetype=mimetype)


# ── ERP REST APIs ──

@app.route("/api/v1/inspections", methods=["GET"])
def erp_get_inspections():
    """ERP用: 検査履歴の取得（フィルタリング可能）"""
    label_filter = request.args.get("label", "")
    cable_id = request.args.get("cable_id", "")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    result = get_filtered_images(
        label=label_filter,
        cable_id=cable_id,
        limit=limit,
        offset=offset,
    )
    return jsonify(result)

@app.route("/api/v1/inspections/stats", methods=["GET"])
def erp_get_inspections_stats():
    """ERP用: 全体統計の取得"""
    stats = get_statistics()
    return jsonify(stats)


# ── AI Routes ──

@app.route('/api/predict', methods=['POST'])
def predict_endpoint():
    """Predict anomaly score for a given image path."""
    data = request.json
    filepath = data.get('filepath')
    
    if not filepath:
        return jsonify({"error": "Filepath required"}), 400
        
    if not os.path.exists(filepath):
         # Try absolute path if relative
         abs_path = os.path.abspath(filepath)
         if os.path.exists(abs_path):
             filepath = abs_path
         else:
             return jsonify({"error": "File not found"}), 404
        
    result = ai_engine.predict(filepath)
    return jsonify(result)

@app.route('/api/train', methods=['POST'])
def train_endpoint():
    """Start model training in background."""
    global training_active
    
    with training_lock:
        if training_active:
            return jsonify({"status": "error", "message": "Training already in progress"}), 409
        training_active = True
    
    data = request.json or {}
    model_type = data.get('model_type', 'patchcore')

    def train_task():
        global training_active
        try:
            print(f"Training started ({model_type})...")
            result = ai_engine.train(model_type=model_type)
            print(f"Training finished: {result}")
        except Exception as e:
            print(f"Training failed: {e}")
        finally:
            with training_lock:
                training_active = False
                
    thread = threading.Thread(target=train_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": f"{model_type} training started in background"})

@app.route('/api/training-status')
def training_status():
    global training_active
    return jsonify({"active": training_active})

@app.route('/api/models')
def list_models():
    """List available model types and their status."""
    return jsonify(ai_engine.get_available_models())

@app.route('/api/versions')
def list_versions():
    """List all trained versions for a model type."""
    model_type = request.args.get('model_type', 'patchcore')
    versions = ai_engine.list_versions(model_type)
    current = ai_engine._get_current_version(model_type)
    return jsonify({"model_type": model_type, "current": current, "versions": versions})

@app.route('/api/rollback', methods=['POST'])
def rollback():
    """Rollback to a specific model version."""
    data = request.json or {}
    version = data.get('version')
    model_type = data.get('model_type', 'patchcore')
    if not version:
        return jsonify({"error": "version required"}), 400
    result = ai_engine.rollback_to_version(version, model_type)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400



# ── Design Spec Analysis ──

from modules.vlm import analyze_spec
from modules.cost import calculate_estimate
import tempfile

@app.route("/api/analyze-spec", methods=["POST"])
def analyze_spec_endpoint():
    """デザイン仕様書画像を解析して構成要素を抽出"""
    data = request.json or {}
    image_data = data.get("image", "") # Base64 string
    
    if not image_data:
        return jsonify({"error": "No image data provided"}), 400
        
    try:
        # Save temp file for Gemini
        header, encoded = image_data.split(",", 1)
        decoded = base64.b64decode(encoded)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(decoded)
            tmp_path = tmp.name
            
        result = analyze_spec(tmp_path)
        os.unlink(tmp_path) # Clean up
        
        if "error" in result:
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/estimate-cost", methods=["POST"])
def estimate_cost_endpoint():
    """構成要素からコスト試算"""
    data = request.json or {}
    components = data.get("components", [])
    
    if not components:
        return jsonify({"error": "No components provided"}), 400
        
    estimate = calculate_estimate(components)
    return jsonify(estimate)


# ── Auto-Retraining Scheduler ──
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import datetime
from modules.models import ImageRecord

def scheduled_retraining():
    """Nightly job: Check if new OK images were added today and retrain the model."""
    with app.app_context():
        # Check if any new "ok" images were added since midnight
        today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_oks = ImageRecord.query.filter(ImageRecord.label == 'ok', ImageRecord.timestamp >= today).count()
        
        if new_oks > 0:
            print(f"[MLOps] Found {new_oks} new OK images today. Starting nightly retraining...")
            global training_active
            with training_lock:
                if not training_active:
                    training_active = True
                    try:
                        ai_engine.train(model_type='patchcore')
                        print("[MLOps] Nightly retraining completed.")
                    except Exception as e:
                        print(f"[MLOps] Nightly retraining failed: {e}")
                    finally:
                        training_active = False
        else:
            print("[MLOps] No new OK images today. Skipping retraining.")

scheduler = BackgroundScheduler()
# Run every day at 2:00 AM
scheduler.add_job(func=scheduled_retraining, trigger="cron", hour=2, minute=0)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# ── 起動 ──

if __name__ == "__main__":
    print("=" * 50)
    print("  QC-Check 02 - 画像検査キャプチャステーション")
    print("=" * 50)
    print(f"  データ保存先: {config.DATA_DIR}")
    print(f"  サーバー: http://localhost:{config.FLASK_PORT}")
    print("  カメラはブラウザ側で制御します (WebRTC)")
    print("=" * 50)

    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True,
    )
