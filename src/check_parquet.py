import duckdb
from src.config import DATA_DIR, DAY

con = duckdb.connect()
path = str(DATA_DIR / "parquet" / DAY / "*.parquet")

print(con.sql(f"""
    SELECT version, nac_p, count(*) AS n
    FROM '{path}'
    GROUP BY ALL ORDER BY version, nac_p
"""))