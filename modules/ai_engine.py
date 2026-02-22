"""
AI Engine for QC-Check 02
Anomalib-based visual anomaly detection with PatchCore.

Features:
- PatchCore training on "OK" samples (unsupervised)
- PyTorch inference with anomaly score + heatmap
- OpenVINO export for fast inference
- Multi-model support (PatchCore, EfficientAD, Padim)
- Model versioning with rollback
"""

import base64
import io
import json
import os
import shutil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch

# Monkeypatch os.symlink and os.unlink for Windows non-admin
if os.name == 'nt':
    try:
        os.symlink("test_source", "test_dest")
        os.remove("test_dest")
    except OSError:
        def symlink_mock(src, dst, target_is_directory=None):
            pass
        os.symlink = symlink_mock

        real_unlink = os.unlink
        def unlink_mock(path):
            try:
                real_unlink(path)
            except OSError:
                pass
        os.unlink = unlink_mock

from anomalib.data import Folder
from anomalib.deploy import ExportType, OpenVINOInferencer
from anomalib.engine import Engine
from anomalib.models import Patchcore
from torchvision.transforms.v2 import Compose, Resize, ToDtype, Normalize

# Config
DATA_ROOT = Path("data")
MODEL_DIR = Path("models")
OPENVINO_DIR = MODEL_DIR / "openvino"

# Supported models
SUPPORTED_MODELS = {
    "patchcore": "Patchcore",
    "padim": "Padim",
    "efficientad": "EfficientAd",
}

DEFAULT_BACKBONES = {
    "patchcore": "resnet18",
    "padim": "resnet18",
    "efficientad": None,
}


class AIEngine:
    """Anomalib-based AI engine for visual anomaly detection."""

    def __init__(self):
        self.model = None
        self.metadata = None
        self.inferencer = None
        self.active_model_type = "patchcore"
        self._load_inference_model()

    # ── Model Loading ──

    def _load_inference_model(self, model_type: str = "patchcore"):
        """Load the best available model for inference."""
        self.active_model_type = model_type
        model_dir = MODEL_DIR / model_type.capitalize()

        try:
            # 1. Try OpenVINO
            ov_dir = MODEL_DIR / "openvino"
            if (ov_dir / "model.xml").exists() and (ov_dir / "metadata.json").exists():
                print(f"Loading OpenVINO model...")
                self.inferencer = OpenVINOInferencer(
                    path=ov_dir / "model.xml",
                    metadata=ov_dir / "metadata.json"
                )
                self.model = None
                return

            # 2. Try latest .ckpt
            ckpts = list(model_dir.rglob("*.ckpt"))
            if ckpts:
                latest_ckpt = max(ckpts, key=os.path.getmtime)
                print(f"Loading checkpoint: {latest_ckpt}")
                ModelClass = self._get_model_class(model_type)
                self.model = ModelClass.load_from_checkpoint(str(latest_ckpt))
                self.model.eval()
                self.inferencer = None
                return

            print(f"No {model_type} model found. Training required.")
        except Exception as e:
            print(f"Failed to load model: {e}")

    def _get_model_class(self, model_type: str):
        """Get Anomalib model class by name."""
        if model_type == "patchcore":
            from anomalib.models import Patchcore
            return Patchcore
        elif model_type == "padim":
            from anomalib.models import Padim
            return Padim
        elif model_type == "efficientad":
            from anomalib.models import EfficientAd
            return EfficientAd
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def _get_transform(self):
        return Compose([
            Resize((256, 256)),
            ToDtype(torch.float32, scale=True),
            Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    # ── Training ──

    def train(self, model_type: str = "patchcore", expected_normal_count: int = 10) -> dict:
        """
        Train a model on 'ok' images.
        Returns dict with success, message, and version info.
        """
        ok_dir = DATA_ROOT / "ok"
        all_ok = list(ok_dir.rglob("*.jpg")) + list(ok_dir.rglob("*.png"))
        if len(all_ok) < expected_normal_count:
            return {"success": False, "error": f"Need at least {expected_normal_count} OK images (found {len(all_ok)})"}

        # Prepare temp training directory
        train_root = DATA_ROOT / "train_temp"
        if train_root.exists():
            shutil.rmtree(train_root)
        (train_root / "good").mkdir(parents=True)

        for img_path in all_ok:
            shutil.copy(img_path, train_root / "good" / img_path.name)

        transform = self._get_transform()

        datamodule = Folder(
            name="cable",
            root=str(train_root),
            normal_dir="good",
            abnormal_dir=None,
            train_batch_size=1,
            eval_batch_size=1,
            num_workers=0,
            train_augmentations=transform,
            val_augmentations=transform,
            test_augmentations=transform,
        )

        # Create model
        ModelClass = self._get_model_class(model_type)
        backbone = DEFAULT_BACKBONES.get(model_type)
        if backbone:
            self.model = ModelClass(backbone=backbone, pre_trained=True, coreset_sampling_ratio=0.1)
        else:
            self.model = ModelClass()

        model_out_dir = MODEL_DIR / model_type.capitalize()
        engine = Engine(
            default_root_dir=str(model_out_dir),
            accelerator="cpu",
            devices=1,
            max_epochs=1,
        )

        print(f"Starting {model_type} training...")
        try:
            engine.fit(model=self.model, datamodule=datamodule)
        except Exception as e:
            if train_root.exists():
                shutil.rmtree(train_root)
            raise e

        # Try OpenVINO export
        print("Exporting model...")
        try:
            engine.export(
                model=self.model,
                export_type=ExportType.OPENVINO,
                export_root=str(MODEL_DIR),
            )
        except Exception as e:
            print(f"OpenVINO export failed: {e}")

        # Cleanup
        if train_root.exists():
            shutil.rmtree(train_root)

        version = self._get_current_version(model_type)

        self._load_inference_model(model_type)
        return {
            "success": True,
            "message": f"{model_type} training completed",
            "model_type": model_type,
            "version": version,
        }

    # ── Inference ──

    def predict(self, image_path: str) -> dict:
        """Predict anomaly score for an image. Returns score, label, and optional heatmap."""
        if self.inferencer:
            return self._predict_openvino(image_path)
        elif self.model:
            return self._predict_pytorch(image_path)
        else:
            return {"error": "Model not loaded. Please train first."}

    def _predict_openvino(self, image_path: str) -> dict:
        """OpenVINO inference (fast)."""
        try:
            predictions = self.inferencer.predict(image=image_path)
            score = float(predictions.pred_score)
            return {
                "score": round(score, 4),
                "label": "ng" if score > 0.5 else "ok",
                "method": "openvino",
            }
        except Exception as e:
            return {"error": str(e)}

    def _predict_pytorch(self, image_path: str) -> dict:
        """PyTorch inference with heatmap generation."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Failed to load image"}
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            transform = self._get_transform()
            from torchvision.transforms.v2.functional import to_image
            input_tensor = to_image(image_rgb)
            input_tensor = transform(input_tensor).unsqueeze(0)

            with torch.no_grad():
                output = self.model(input_tensor)

            # Anomalib 2.x InferenceBatch: [0]=pred_score, [1]=pred_label, [2]=anomaly_map, [3]=pred_mask
            score = 0.0
            heatmap_b64 = None

            if hasattr(output, 'pred_score'):
                score = float(output.pred_score.item()) if output.pred_score.numel() == 1 else float(output.pred_score[0].item())
            elif isinstance(output, (tuple, list)) and len(output) >= 1:
                score_tensor = output[0]
                if isinstance(score_tensor, torch.Tensor):
                    score = float(score_tensor.item()) if score_tensor.numel() == 1 else float(score_tensor[0].item())

            # Extract anomaly map for heatmap
            anomaly_map = None
            if hasattr(output, 'anomaly_map'):
                anomaly_map = output.anomaly_map
            elif isinstance(output, (tuple, list)) and len(output) >= 3:
                anomaly_map = output[2]

            if anomaly_map is not None and isinstance(anomaly_map, torch.Tensor):
                heatmap_b64 = self._generate_heatmap(image, anomaly_map)

            result = {
                "score": round(score, 4),
                "label": "ng" if score > 0.5 else "ok",
                "method": "pytorch",
            }
            if heatmap_b64:
                result["heatmap"] = heatmap_b64

            return result

        except Exception as e:
            return {"error": f"PyTorch inference failed: {e}"}

    def _generate_heatmap(self, original_image: np.ndarray, anomaly_map: torch.Tensor) -> Optional[str]:
        """Generate a heatmap overlay and return as base64 JPEG string."""
        try:
            amap = anomaly_map.squeeze().cpu().numpy()

            if amap.max() > amap.min():
                amap = (amap - amap.min()) / (amap.max() - amap.min())
            amap = (amap * 255).astype(np.uint8)

            h, w = original_image.shape[:2]
            amap_resized = cv2.resize(amap, (w, h))

            heatmap_colored = cv2.applyColorMap(amap_resized, cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(original_image, 0.6, heatmap_colored, 0.4, 0)

            _, buffer = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            print(f"Heatmap generation failed: {e}")
            return None

    # ── Model Versioning ──

    def _get_current_version(self, model_type: str = "patchcore") -> str:
        """Get the latest version number."""
        model_dir = MODEL_DIR / model_type.capitalize()
        if not model_dir.exists():
            return "v0"
        # Look inside cable subdirectory (Anomalib default structure)
        cable_dir = model_dir / "cable"
        if not cable_dir.exists():
            cable_dir = model_dir
        versions = [d.name for d in cable_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        if not versions:
            return "v0"
        nums = [int(v[1:]) for v in versions if v[1:].isdigit()]
        return f"v{max(nums)}" if nums else "v0"

    def list_versions(self, model_type: str = "patchcore") -> list:
        """List all available model versions."""
        model_dir = MODEL_DIR / model_type.capitalize() / "cable"
        if not model_dir.exists():
            return []
        versions = []
        for d in sorted(model_dir.iterdir()):
            if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit():
                ckpts = list(d.rglob("*.ckpt"))
                versions.append({
                    "version": d.name,
                    "has_checkpoint": len(ckpts) > 0,
                    "path": str(d),
                })
        return versions

    def rollback_to_version(self, version: str, model_type: str = "patchcore") -> dict:
        """Rollback to a specific model version."""
        model_dir = MODEL_DIR / model_type.capitalize()
        version_dir = model_dir / "cable" / version
        if not version_dir.exists():
            return {"success": False, "error": f"Version {version} not found"}

        ckpts = list(version_dir.rglob("*.ckpt"))
        if not ckpts:
            return {"success": False, "error": f"No checkpoint found in {version}"}

        latest_dir = model_dir / "cable" / "latest"
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        shutil.copytree(version_dir, latest_dir)

        self._load_inference_model(model_type)
        return {"success": True, "message": f"Rolled back to {version}", "version": version}

    def get_available_models(self) -> list:
        """List all supported model types."""
        result = []
        for key, name in SUPPORTED_MODELS.items():
            model_dir = MODEL_DIR / name
            has_model = bool(list(model_dir.rglob("*.ckpt"))) if model_dir.exists() else False
            result.append({
                "type": key,
                "name": name,
                "trained": has_model,
                "active": key == self.active_model_type,
            })
        return result


ai_engine = AIEngine()
