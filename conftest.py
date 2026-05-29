import os
import sys

ROOT = os.path.dirname(__file__)
BACKEND_PATH = os.path.join(ROOT, "dataverse_backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)
