from concurrent.futures import ProcessPoolExecutor

import pyarrow as pa
import pyarrow.parquet as pq
from src.adsb_io import list_trace_files, load_trace, iter_points
from src.config import DATA_DIR, DAY

STEP_S = 60               # keep at most one point per aircraft per 60 s
VALID_VERSIONS = {1, 2}
OUT_DIR = DATA_DIR / "parquet" / DAY
CHUNK = 2000              # files per worker task

SCHEMA = pa.schema([
    ("hex", pa.string()),
    ("ts", pa.int64()),
    ("lat", pa.float32()),
    ("lon", pa.float32()),
    ("alt_ft", pa.float32()),
    ("on_ground", pa.bool_()),
    ("nac_p", pa.int8()),
    ("nic", pa.int8()),
    ("version", pa.int8()),
])


def process_chunk(args):
    chunk_id, paths = args
    cols = {name: [] for name in SCHEMA.names}

    for path in paths:
        data = load_trace(path)
        if data is None:
            continue
        hex_id = data.get("icao")
        last_ts = None

        for ts, lat, lon, alt, nac_p, nic, version in iter_points(data):
            if version not in VALID_VERSIONS or nac_p is None or not (0 <= nac_p <= 11):
                continue
            if last_ts is not None and ts - last_ts < STEP_S:
                continue
            last_ts = ts

            on_ground = alt == "ground"
            cols["hex"].append(hex_id)
            cols["ts"].append(int(ts))
            cols["lat"].append(lat)
            cols["lon"].append(lon)
            cols["alt_ft"].append(None if on_ground or not isinstance(alt, (int, float)) else alt)
            cols["on_ground"].append(on_ground)
            cols["nac_p"].append(nac_p)
            cols["nic"].append(nic)
            cols["version"].append(version)

    table = pa.table(cols, schema=SCHEMA)
    pq.write_table(table, OUT_DIR / f"part_{chunk_id:04d}.parquet", compression="zstd")
    return table.num_rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = list_trace_files()
    chunks = [(i, files[i:i + CHUNK]) for i in range(0, len(files), CHUNK)]
    print(f"{len(files)} files in {len(chunks)} chunks")

    total = 0
    with ProcessPoolExecutor() as pool:
        for n in pool.map(process_chunk, chunks):
            total += n
            print(f"  +{n:,} rows (total {total:,})")
    print("Done ->", OUT_DIR)


if __name__ == "__main__":
    main()