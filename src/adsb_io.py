import glob
import gzip
import json

from src.config import DATA_DIR, DAY

def list_trace_files():
    return glob.glob(str(DATA_DIR / DAY / "traces" / "*" / "trace_full_*.json"))


def load_trace(path):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        print(f"Skipping {path}: {e}")
        return None


def iter_points(data):
    """Yield (timestamp, lat, lon, alt, nac_p, nic, version) for each trace point.

    Extra fields only appear on some points, so the last known values
    are carried forward along the aircraft's track.
    """
    base_ts = data.get("timestamp", 0)
    nac_p = nic = version = None

    for p in data.get("trace", []):
        if len(p) < 3 or p[1] is None or p[2] is None:
            continue

        if len(p) > 8 and isinstance(p[8], dict):
            info = p[8]
            nac_p = info.get("nac_p", nac_p)
            nic = info.get("nic", nic)
            version = info.get("version", version)

        alt = p[3] if len(p) > 3 else None
        yield base_ts + p[0], p[1], p[2], alt, nac_p, nic, version
