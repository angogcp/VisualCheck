import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import torch

# Monkeypatch os.symlink and os.unlink for Windows non-admin
if os.name == 'nt':
    try:
        os.symlink("test_source", "test_dest")
        os.remove("test_dest")
    except OSError:
        # Define a no-op symlink function
        def symlink_mock(src, dst, target_is_directory=None):
            print(f"Skipping symlink: {src} -> {dst}")
        os.symlink = symlink_mock
        
        # Wrap unlink to ignore errors for 'latest' symlink which might be a dir or missing
        real_unlink = os.unlink
        def unlink_mock(path):
            try:
                real_unlink(path)
            except OSError:
                print(f"Skipping unlink: {path}")
        os.unlink = unlink_mock

from anomalib.data import Folder
from anomalib.deploy import ExportType, OpenVINOInferencer
from anomalib.engine import Engine
from anomalib.models import Patchcore
from torchvision.transforms.v2 import Compose, Resize, ToDtype, Normalize

# Config
DATA_ROOT = Path("data")
MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "model.pt"
OPENVINO_DIR = MODEL_DIR / "openvino"

class AIEngine:
    def __init__(self):
        self.model = None
        self.metadata = None
        self.inferencer = None
        self._load_inference_model()

    def _load_inference_model(self):
        """Load OpenVINO model for fast inference if available, else PyTorch checkpoint."""
        try:
            # 1. Try OpenVINO
            if (OPENVINO_DIR / "model.xml").exists() and (OPENVINO_DIR / "metadata.json").exists():
                print("Loading OpenVINO model...")
                self.inferencer = OpenVINOInferencer(
                    path=OPENVINO_DIR / "model.xml",
                    metadata=OPENVINO_DIR / "metadata.json"
                )
                return

            # 2. Try PyTorch .pt
            if MODEL_PATH.exists():
                print("Loading PyTorch model (pt)...")
                self.model = Patchcore.load_from_checkpoint(str(MODEL_PATH))
                self.model.eval()
                return

            # 3. Try finding latest .ckpt
            ckpts = list(MODEL_DIR.rglob("*.ckpt"))
            if ckpts:
                latest_ckpt = max(ckpts, key=os.path.getmtime)
                print(f"Loading PyTorch checkpoint: {latest_ckpt}")
                self.model = Patchcore.load_from_checkpoint(str(latest_ckpt))
                self.model.eval()
                return

            print("No model found. Training required.")
        except Exception as e:
            print(f"Failed to load model: {e}")

    def _get_transform(self):
        return Compose([
            Resize((256, 256)),
            ToDtype(torch.float32, scale=True),
            Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def train(self, expected_normal_count: int = 10) -> dict:
        """
        Train PatchCore model on 'ok' images.
        Requires at least `expected_normal_count` images in data/ok.
        """
        ok_dir = DATA_ROOT / "ok"
        if not ok_dir.exists() or len(list(ok_dir.glob("*.jpg"))) < expected_normal_count:
            return {"success": False, "error": f"Need at least {expected_normal_count} OK images for training"}

        train_root = DATA_ROOT / "train_temp"
        if train_root.exists():
            shutil.rmtree(train_root)
        train_root.mkdir(parents=True)
        
        # Copy OK images to train/good
        (train_root / "good").mkdir()
        for img_path in ok_dir.glob("*.jpg"):
            shutil.copy(img_path, train_root / "good" / img_path.name)
            
        # Transform for resizing (Anomalib 2.x expects torchvision.transforms.v2)
        transform = self._get_transform()

        datamodule = Folder(
            name="cable",
            root=str(train_root),
            normal_dir="good",
            abnormal_dir=None,
            train_batch_size=1,
            eval_batch_size=1,
            num_workers=0, # Avoid Windows multiprocessing issues
            train_augmentations=transform,
            val_augmentations=transform,
            test_augmentations=transform,
        )

        # Model
        self.model = Patchcore(backbone="resnet18", pre_trained=True, coreset_sampling_ratio=0.1)

        # Engine
        engine = Engine(
            default_root_dir=str(MODEL_DIR),
            accelerator="cpu",
            devices=1,
            max_epochs=1,
        )
        
        print("Starting training...")
        try:
            engine.fit(model=self.model, datamodule=datamodule)
        except Exception as e:
            # Cleanup and re-raise to see error
            if train_root.exists(): shutil.rmtree(train_root)
            raise e
        
        # Export
        print("Exporting model...")
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        try:
            # Export to OpenVINO
            engine.export(
                model=self.model,
                export_type=ExportType.OPENVINO,
                export_root=str(MODEL_DIR),
            )
        except Exception as e:
            print(f"OpenVINO export failed: {e}")

        # cleanup
        if train_root.exists():
            shutil.rmtree(train_root)
            
        self._load_inference_model()
        return {"success": True, "message": "Training completed"}

    def predict(self, image_path: str) -> dict:
        """Predict anomaly score for an image."""
        if self.inferencer:
            try:
                # OpenVINO inference
                predictions = self.inferencer.predict(image=image_path)
                # predictions is an ImageResult object
                return {
                    "score": float(predictions.pred_score),
                    "label": "ng" if predictions.pred_score > 0.5 else "ok",
                    "heatmap": predictions.heat_map
                }
            except Exception as e:
                return {"error": str(e)}
        elif self.model:
            # PyTorch inference
            try:
                image = cv2.imread(image_path)
                if image is None:
                    return {"error": "Failed to load image"}
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Preprocess
                transform = self._get_transform()
                from torchvision.transforms.v2.functional import to_image
                input_tensor = to_image(image)
                input_tensor = transform(input_tensor).unsqueeze(0) # Add batch dim

                # Inference
                with torch.no_grad():
                    # PatchCore returns: score, anomaly_map (if configured)
                    # output might be a scalar tensor or tuple
                    output = self.model(input_tensor)
                
                # Handle output based on type
                score = 0.0
                heatmap = None
                
                # Anomalib 2.x forward() often returns anomaly map if not predicting?
                # Actually, check attribute 'pred_score' if output is an object, or if tuple
                # For now just return the raw score if possible
                
                if isinstance(output, torch.Tensor):
                     # If scalar, it's score? Or map?
                     if output.numel() == 1:
                         score = output.item()
                     else:
                         # Likely anomaly map
                         score = getattr(output, "max", lambda: 0.0)().item() if hasattr(output, "max") else 0.0
                         # TODO: Generate heatmap from map
                elif hasattr(output, "pred_score"):
                     score = output.pred_score.item()
                elif isinstance(output, tuple):
                     # (anomaly_map, pred_score) ??
                     score = 0.5 # Placeholder
                
                return {
                    "score": score,
                    "label": "ng" if score > 0.5 else "ok", # Threshold needs tuning
                    "message": "PyTorch inference used (fallback)"
                 }

            except Exception as e:
                return {"error": f"PyTorch inference failed: {e}"}
        else:
            return {"error": "Model not loaded"}

ai_engine = AIEngine()

