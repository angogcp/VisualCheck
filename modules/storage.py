"""
画像保存・管理モジュール
Image storage and metadata management using SQLAlchemy.
"""
import base64
import os
import shutil
from datetime import datetime
from sqlalchemy import func

import config
from modules.models import db, ImageRecord

def init_db(app):
    """Initialize DB and migrate CSV if it exists."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Optional: migrate CSV if we are starting fresh with DB but have CSV
        migrate_csv_to_db()

def migrate_csv_to_db():
    """Migrate data from metadata.csv to SQLite if DB is empty."""
    import csv
    if not os.path.exists(config.METADATA_CSV):
        return

    # Check if DB is empty
    if ImageRecord.query.first() is not None:
        return

    with open(config.METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            try:
                dt = datetime.fromisoformat(row.get("timestamp", ""))
            except (ValueError, TypeError):
                dt = datetime.utcnow()
                
            rec = ImageRecord(
                timestamp=dt,
                filename=row.get("filename", ""),
                filepath=row.get("filepath", ""),
                label=row.get("label", "unlabeled"),
                cable_id=row.get("cable_id", ""),
                file_size_bytes=int(row.get("file_size_bytes", 0) or 0)
            )
            records.append(rec)
            
        if records:
            db.session.bulk_save_objects(records)
            db.session.commit()
            print(f"Migrated {len(records)} records from CSV to Database.")

def save_image_from_base64(
    data_url: str,
    label: str = "unlabeled",
    cable_id: str = "",
) -> tuple[str, str]:
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
    ts_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    cable_part = f"_{cable_id}" if cable_id else ""
    filename = f"{ts_str}{cable_part}.jpg"
    filepath = os.path.join(save_dir, filename)

    with open(filepath, "wb") as f:
        f.write(image_data)

    file_size = len(image_data)
    
    # Save to DB
    record = ImageRecord(
        timestamp=timestamp,
        filename=filename,
        filepath=filepath,
        label=label,
        cable_id=cable_id,
        file_size_bytes=file_size
    )
    db.session.add(record)
    db.session.commit()

    return filepath, filename

def _ensure_date_dir(base_dir: str) -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    path = os.path.join(base_dir, date_str)
    os.makedirs(path, exist_ok=True)
    return path

def relabel_image(filepath: str, new_label: str) -> str:
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

    # Update DB
    record = ImageRecord.query.filter_by(filename=filename).first()
    if record:
        record.label = new_label
        record.filepath = new_path
        db.session.commit()

    return new_path

def delete_image(filepath: str) -> bool:
    filename = os.path.basename(filepath)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    # Delete from DB
    record = ImageRecord.query.filter_by(filename=filename).first()
    if record:
        db.session.delete(record)
        db.session.commit()

    return True

def get_recent_images(n: int = 20) -> list[dict]:
    records = ImageRecord.query.order_by(ImageRecord.timestamp.desc()).limit(n).all()
    result = []
    for r in records:
        data = r.to_dict()
        if os.path.exists(data["filepath"]):
            result.append(data)
    return result

def get_filtered_images(
    label: str = "",
    cable_id: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = ImageRecord.query

    if label:
        query = query.filter_by(label=label)
    if cable_id:
        query = query.filter(ImageRecord.cable_id.ilike(f"%{cable_id}%"))
        
    total = query.count()
    records = query.order_by(ImageRecord.timestamp.desc()).offset(offset).limit(limit).all()
    
    images = []
    for r in records:
        data = r.to_dict()
        if os.path.exists(data["filepath"]):
            images.append(data)
            
    return {
        "images": images,
        "total": total,
        "has_more": (offset + limit) < total,
    }

def get_statistics() -> dict:
    stats = {"ok": 0, "ng": 0, "unlabeled": 0, "total": 0}
    
    results = db.session.query(ImageRecord.label, func.count(ImageRecord.id)).group_by(ImageRecord.label).all()
    for label, count in results:
        if label in stats:
            stats[label] = count
        stats["total"] += count
        
    return stats

def get_daily_statistics(days: int = 30) -> list[dict]:
    # Since sqlite dates can be tricky, we'll fetch recently and aggregate in python 
    # for simplicity across different DB dialects right now.
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    records = ImageRecord.query.filter(ImageRecord.timestamp >= cutoff).all()
    
    from collections import defaultdict
    daily = defaultdict(lambda: {"ok": 0, "ng": 0, "unlabeled": 0, "total": 0})
    
    for r in records:
        date_key = r.timestamp.strftime("%Y-%m-%d")
        if r.label in daily[date_key]:
            daily[date_key][r.label] += 1
        daily[date_key]["total"] += 1
        
    result = []
    for date_key in sorted(daily.keys(), reverse=True):
        entry = {"date": date_key}
        entry.update(daily[date_key])
        result.append(entry)
        
    return result

def export_csv_content() -> str:
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "filename", "filepath", "label",
        "cable_id", "file_size_bytes",
    ])
    
    for r in ImageRecord.query.order_by(ImageRecord.timestamp.asc()).all():
        writer.writerow([
            r.timestamp.isoformat(),
            r.filename,
            r.filepath,
            r.label,
            r.cable_id,
            r.file_size_bytes
        ])
        
    return output.getvalue()
