import gzip, json, glob
from config import DATA_DIR, DAY

files = glob.glob(str(DATA_DIR / DAY / "traces" / "*" / "trace_full_*.json"))
print(len(files), "aircraft files")

with gzip.open(files[0], "rt") as fh:
    d = json.load(fh)

print(d.keys())
for p in d["trace"][:5]:
    print(p)