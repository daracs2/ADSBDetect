import os
from pathlib import Path

# Override with: export DATA_DIR=/path/to/data
DATA_DIR = Path(os.environ.get("DATA_DIR", Path.home() / "Downloads" / "ADSBDetect"))
DAY = "2026.11.08"