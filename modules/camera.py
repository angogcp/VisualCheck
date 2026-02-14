"""
カメラモジュール — WebRTC アーキテクチャメモ
Camera module for QC inspection capture station.

Architecture Note (Python 3.15):
    Camera capture is handled client-side via WebRTC / getUserMedia.
    The browser captures video frames using the <video> element,
    draws them to a <canvas>, and sends the frame as a base64-encoded
    JPEG to the Flask backend via POST /capture.

    This module is retained as a reference for the original OpenCV-based
    design and will be extended in Phase 2 if server-side processing
    is needed (e.g., with a compatible image library).

Original Design (unused):
    - CameraManager class wrapping OpenCV VideoCapture
    - MJPEG streaming endpoint for browser live preview
    - Mock mode fallback with synthetic test patterns
"""


class CameraInfo:
    """カメラ状態の情報を提供するクラス（WebRTC版）"""

    def __init__(self):
        self.mode = "webrtc"

    @property
    def description(self) -> str:
        return "ブラウザ側 WebRTC (getUserMedia) によるカメラ制御"

    @property
    def is_server_side(self) -> bool:
        return False

    def __repr__(self):
        return f"CameraInfo(mode='{self.mode}')"
