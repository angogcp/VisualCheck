import sys
import os
from pathlib import Path
import cv2
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.ai_engine import AIEngine, DATA_ROOT

def generate_mock_data():
    ok_dir = DATA_ROOT / "ok"
    ok_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating mock data in {ok_dir}...")
    for i in range(15):
        # Create a dummy image (gray background with some noise)
        img = np.random.randint(100, 150, (256, 256, 3), dtype=np.uint8)
        cv2.putText(img, "OK", (50, 128), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)
        cv2.imwrite(str(ok_dir / f"mock_{i:03d}.jpg"), img)

def main():
    generate_mock_data()
    
    print("Initializing AI Engine...")
    engine = AIEngine()
    
    print("Starting training...")
    result = engine.train(expected_normal_count=5)
    
    print("Training result:", result)
    
    if result.get("success"):
        print("Training successful!")
        # Test prediction
        test_img = DATA_ROOT / "ok" / "mock_000.jpg"
        print(f"Predicting on {test_img}...")
        pred = engine.predict(str(test_img))
        print("Prediction:", pred)
    else:
        print("Training failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
