"""
QC-Check 02 — メインアプリケーション
Flask web application for cable inspection capture station.

Architecture: Camera capture is handled client-side via WebRTC/getUserMedia.
Images are sent as base64 data URLs from the browser canvas.
This avoids numpy/opencv dependency issues with Python 3.15.
"""
import os

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
)

app = Flask(__name__)


# ── ページルート ──

@app.route("/")
def index():
    """メイン画面（キャプチャ）"""
    stats = get_statistics()
    recent = get_recent_images(12)
    return render_template(
        "index.html",
        stats=stats,
        recent=recent,
        active_page="capture",
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
        
    def train_task():
        global training_active
        try:
            print("Training started...")
            # Use small count for quick testing if in dev mode, or default
            result = ai_engine.train()
            print(f"Training finished: {result}")
        except Exception as e:
            print(f"Training failed: {e}")
        finally:
            with training_lock:
                training_active = False
                
    thread = threading.Thread(target=train_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": "Training started in background"})

@app.route('/api/training-status')
def training_status():
    global training_active
    return jsonify({"active": training_active})


# ── 起動 ──

if __name__ == "__main__":
    print("=" * 50)
    print("  QC-Check 02 — 画像検査キャプチャステーション")
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
