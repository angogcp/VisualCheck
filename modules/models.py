from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ImageRecord(db.Model):
    __tablename__ = 'image_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    filename = db.Column(db.String(255), nullable=False, index=True)
    filepath = db.Column(db.String(512), nullable=False)
    label = db.Column(db.String(50), default="unlabeled", index=True)
    cable_id = db.Column(db.String(100), default="", index=True)
    file_size_bytes = db.Column(db.Integer, default=0)
    score = db.Column(db.Float, nullable=True) # For future ML sorting

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "filename": self.filename,
            "filepath": self.filepath,
            "label": self.label,
            "cable_id": self.cable_id,
            "file_size_bytes": self.file_size_bytes,
            "score": self.score,
            "exists": True # populated dynamically in storage.py usually, keeping compat
        }
