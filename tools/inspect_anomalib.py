import inspect
import sys
import os

# Redirect stdout to file
sys.stdout = open("anomalib_inspection.txt", "w", encoding="utf-8")

try:
    print("=== anomalib.data.Folder ===")
    from anomalib.data import Folder
    print(inspect.signature(Folder))
    print(inspect.getdoc(Folder))
    print("\n")
except Exception as e:
    print(f"Error inspecting Folder: {e}")

try:
    print("=== anomalib.models.Patchcore ===")
    from anomalib.models import Patchcore
    print(inspect.signature(Patchcore))
    print(inspect.getdoc(Patchcore))
    print("\n")
except Exception as e:
    print(f"Error inspecting Patchcore: {e}")

try:
    print("=== anomalib.engine.Engine ===")
    from anomalib.engine import Engine
    print(inspect.signature(Engine))
    print(inspect.getdoc(Engine))
    print("\n")
except Exception as e:
    print(f"Error inspecting Engine: {e}")

try:
    print("=== anomalib.deploy ===")
    import anomalib.deploy
    print(dir(anomalib.deploy))
    print("\n")
except Exception as e:
    print(f"Error inspecting deploy: {e}")
