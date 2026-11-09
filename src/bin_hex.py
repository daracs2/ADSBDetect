import json

import duckdb
import h3

from src.config import DATA_DIR, DAY

RES = 4                  # H3 resolution (4 = ~22 km edges, 5 = ~8 km)
DEGRADED_MAX_NACP = 5    # nac_p <= this counts as degraded
MIN_AC_HOURLY = 5        # min aircraft in a cell-hour
MIN_AC_HOURS_DAILY = 20  # min aircraft-hours in a cell for the daily map

SRC = str(DATA_DIR / "parquet" / DAY / "*.parquet")
OUT_DIR = DATA_DIR / "output" / DAY
OUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.sql("INSTALL h3 FROM community; LOAD h3;")

# One row per aircraft per cell per hour. An aircraft counts as degraded
# if at least half of its points in that cell-hour are degraded, so a single
# glitchy sample doesn't flag it.
con.sql(f"""
    CREATE TABLE ac_hour AS
    SELECT
        h3_latlng_to_cell(lat, lon, {RES}) AS cell,
        hex,
        CAST((ts // 3600) % 24 AS INTEGER) AS hour,
        avg((nac_p <= {DEGRADED_MAX_NACP})::INTEGER) >= 0.5 AS degraded
    FROM read_parquet('{SRC}')
    WHERE version = 2 AND NOT on_ground
    GROUP BY cell, hex, hour
""")

con.sql(f"""
    CREATE TABLE hourly AS
    SELECT cell, hour,
           count(*) AS n_aircraft,
           sum(degraded::INTEGER) AS n_degraded
    FROM ac_hour
    GROUP BY cell, hour
    HAVING count(*) >= {MIN_AC_HOURLY}
""")

con.sql(f"COPY hourly TO '{OUT_DIR / 'hourly.parquet'}' (FORMAT parquet)")

daily = con.sql(f"""
    SELECT cell,
           count(*) AS n_aircraft_hours,
           sum(degraded::INTEGER) AS n_degraded,
           sum(degraded::INTEGER) / count(*) AS frac
    FROM ac_hour
    GROUP BY cell
    HAVING count(*) >= {MIN_AC_HOURS_DAILY}
""").fetchall()

# --- GeoJSON export ---
features = []
for cell, n, d, frac in daily:
    cell_str = h3.int_to_str(cell)
    ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(cell_str)]
    ring.append(ring[0])
    features.append({
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": {"cell": cell_str, "n": n, "degraded": d, "frac": round(frac, 4)},
    })

out = OUT_DIR / "hex_daily.geojson"
with open(out, "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f)
print(f"{len(features)} cells -> {out}")

# --- quick sanity print: worst cells ---
print("\nTop 15 cells by degraded fraction:")
for cell, n, d, frac in sorted(daily, key=lambda r: -r[3])[:15]:
    lat, lng = h3.cell_to_latlng(h3.int_to_str(cell))
    print(f"  {frac:6.1%}  {d:5d}/{n:<6d}  ({lat:.2f}, {lng:.2f})")