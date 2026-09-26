import os
import sys
import tempfile
from pathlib import Path

# Make `ml` importable when pytest is run from the folder root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Tests must never touch the live model registry. `ml.model_registry.DEFAULT_ROOT` is read at
# import time, and `tests/test_api.py` imports the running app's module-level registry -- so
# without this, the training test registered a 2-episode bandit into `ml/checkpoints/` and
# ACTIVATED it, silently replacing the model the real service was serving on every test run.
os.environ["ML_CHECKPOINT_DIR"] = tempfile.mkdtemp(prefix="ml-test-checkpoints-")
