"""
画像保存・管理モジュール
Image storage and metadata management.
Pure Python — no numpy/opencv dependencies.
"""
import base64
import csv
import io
import os
import shutil
from collections import defaultdict
from datetime import datetime, timedelta

import config


def save_image_from_base64(
    data_url: str,
    label: str = "unlabeled",
    cable_id: str = "",
) -> tuple[str, str]:
    """
    Base64 data URL から画像を保存し、メタデータCSVに記録する。

    Args:
        data_url: "data:image/jpeg;base64,..." or "data:image/png;base64,..."
        label: "ok", "ng", "unlabeled"
        cable_id: ケーブル識別ID

    Returns:
        (保存先ファイルパス, ファイル名)
    """
    # Base64デコード
    header, encoded = data_url.split(",", 1)
    image_data = base64.b64decode(encoded)

    label_dirs = {
        "ok": config.OK_DIR,
        "ng": config.NG_DIR,
        "unlabeled": config.UNLABELED_DIR,
    }
    base_dir = label_dirs.get(label, config.UNLABELED_DIR)
    save_dir = _ensure_date_dir(base_dir)

    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]
    cable_part = f"_{cable_id}" if cable_id else ""
    filename = f"{ts_str}{cable_part}.jpg"
    filepath = os.path.join(save_dir, filename)

    with open(filepath, "wb") as f:
        f.write(image_data)

    file_size = len(image_data)
    _append_metadata(timestamp, filepath, filename, label, cable_id, file_size)

    return filepath, filename


def _ensure_date_dir(base_dir: str) -> str:
    """日付別サブフォルダを作成して返す"""
    date_str = datetime.now().strftime("%Y%m%d")
    path = os.path.join(base_dir, date_str)
    os.makedirs(path, exist_ok=True)
    return path


def _append_metadata(
    timestamp: datetime,
    filepath: str,
    filename: str,
    label: str,
    cable_id: str,
    file_size: int,
):
    """メタデータCSVに1行追加する"""
    csv_exists = os.path.exists(config.METADATA_CSV)
    with open(config.METADATA_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow([
                "timestamp", "filename", "filepath", "label",
                "cable_id", "file_size_bytes",
            ])
        writer.writerow([
            timestamp.isoformat(),
            filename,
            filepath,
            label,
            cable_id,
            file_size,
        ])


def relabel_image(filepath: str, new_label: str) -> str:
    """
    既存画像のラベルを変更する（ファイルを移動）。

    Returns:
        新しいファイルパス
    """
    label_dirs = {
        "ok": config.OK_DIR,
        "ng": config.NG_DIR,
        "unlabeled": config.UNLABELED_DIR,
    }
    new_base = label_dirs.get(new_label, config.UNLABELED_DIR)
    new_dir = _ensure_date_dir(new_base)
    filename = os.path.basename(filepath)
    new_path = os.path.join(new_dir, filename)

    if os.path.exists(filepath):
        shutil.move(filepath, new_path)

    _update_csv_label(filename, new_label, new_path)
    return new_path


def _update_csv_label(filename: str, new_label: str, new_path: str):
    """CSVファイルの該当行ラベルを更新"""
    if not os.path.exists(config.METADATA_CSV):
        return

    rows = []
    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4 and row[1] == filename:
                row[2] = new_path
                row[3] = new_label
            rows.append(row)

    with open(config.METADATA_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def delete_image(filepath: str) -> bool:
    """
    画像ファイルを削除し、CSVから該当行を除去する。

    Returns:
        削除成功: True
    """
    filename = os.path.basename(filepath)

    # ファイル削除
    if os.path.exists(filepath):
        os.remove(filepath)

    # CSV から該当行を削除
    if os.path.exists(config.METADATA_CSV):
        rows = []
        with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1] == filename:
                    continue  # この行をスキップ
                rows.append(row)
        with open(config.METADATA_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    return True


def get_recent_images(n: int = 20) -> list[dict]:
    """最近の撮影画像をn件取得する"""
    if not os.path.exists(config.METADATA_CSV):
        return []

    rows = []
    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    recent = rows[-n:]
    recent.reverse()

    result = []
    for row in recent:
        fp = row.get("filepath", "")
        if os.path.exists(fp):
            row["exists"] = True
            result.append(row)

    return result


def get_filtered_images(
    label: str = "",
    cable_id: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    フィルタ付きで画像を取得する。

    Args:
        label: "ok", "ng", "unlabeled", "" (all)
        cable_id: ケーブルIDで部分一致検索
        limit: 取得件数
        offset: オフセット

    Returns:
        {"images": [...], "total": int, "has_more": bool}
    """
    if not os.path.exists(config.METADATA_CSV):
        return {"images": [], "total": 0, "has_more": False}

    all_rows = []
    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # ラベルフィルタ
            if label and row.get("label", "") != label:
                continue
            # ケーブルIDフィルタ（部分一致）
            if cable_id and cable_id.lower() not in row.get("cable_id", "").lower():
                continue
            # ファイル存在チェック
            fp = row.get("filepath", "")
            if os.path.exists(fp):
                row["exists"] = True
                all_rows.append(row)

    # 新しい順に並べ替え
    all_rows.reverse()
    total = len(all_rows)
    page = all_rows[offset:offset + limit]

    return {
        "images": page,
        "total": total,
        "has_more": (offset + limit) < total,
    }


def get_statistics() -> dict:
    """OK / NG / 未分類 の統計を返す"""
    stats = {"ok": 0, "ng": 0, "unlabeled": 0, "total": 0}

    if not os.path.exists(config.METADATA_CSV):
        return stats

    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row.get("label", "unlabeled")
            if label in stats:
                stats[label] += 1
            stats["total"] += 1

    return stats


def get_daily_statistics(days: int = 30) -> list[dict]:
    """
    日別の検査統計を返す（直近n日間）。

    Returns:
        [{"date": "2026-02-14", "ok": 5, "ng": 2, "unlabeled": 1, "total": 8}, ...]
    """
    if not os.path.exists(config.METADATA_CSV):
        return []

    daily = defaultdict(lambda: {"ok": 0, "ng": 0, "unlabeled": 0, "total": 0})

    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row.get("timestamp", "")
            label = row.get("label", "unlabeled")
            try:
                dt = datetime.fromisoformat(ts_str)
                date_key = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            if label in daily[date_key]:
                daily[date_key][label] += 1
            daily[date_key]["total"] += 1

    # 直近n日分を日付順にソート
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = []
    for date_key in sorted(daily.keys(), reverse=True):
        if date_key >= cutoff:
            entry = {"date": date_key}
            entry.update(daily[date_key])
            result.append(entry)

    return result


def export_csv_content() -> str:
    """メタデータCSVの内容を文字列で返す"""
    if not os.path.exists(config.METADATA_CSV):
        return ""
    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        return f.read()

