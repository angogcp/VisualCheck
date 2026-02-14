"""
前処理パイプライン — Phase 2 準備
Preprocessing pipeline for captured cable images.

Architecture Note (Python 3.15):
    The original design used OpenCV + NumPy for server-side image
    preprocessing (resize, normalize, CLAHE, Gaussian blur).
    
    In the current WebRTC architecture:
    - Basic preprocessing (resize, crop) happens client-side via Canvas API
    - Images arrive at the server as base64-encoded JPEGs
    - Server-side preprocessing will be implemented in Phase 2 when
      a compatible image library is available for Python 3.15

Phase 2 Pipeline (planned):
    1. Decode JPEG → pixel array
    2. Resize to model input dimensions (e.g., 224×224)
    3. Normalize pixel values (0-1 range)
    4. Apply contrast enhancement
    5. Return tensor-ready data for model inference
"""

import time


def preprocess_metadata(image_bytes: bytes) -> dict:
    """
    画像バイト列から基本メタデータを抽出する。
    Phase 1 では画像処理なし、メタデータのみ返す。

    Args:
        image_bytes: JPEG 画像のバイト列

    Returns:
        メタデータ辞書
    """
    t_start = time.time()
    meta = {
        "file_size_bytes": len(image_bytes),
        "format": "jpeg",
        "processing_time_ms": 0.0,
        "phase": 1,
        "note": "Phase 1: no server-side image processing",
    }
    meta["processing_time_ms"] = round((time.time() - t_start) * 1000, 2)
    return meta
