import sys
from pathlib import Path

# Make `ml` importable when pytest is run from the folder root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
