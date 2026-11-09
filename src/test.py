import glob
import gzip
import json
import random
from collections import Counter
import matplotlib.pyplot as plt
#local
from src.config import DATA_DIR, DAY
from src.adsb_io import list_trace_files, load_trace, iter_points



def run_sanity_checks(sample_files=5000, seed=42):
    """sample_files=None processes every aircraft file (slow for a full day)."""
    all_files = list_trace_files()
    #temp
    sample_files=len(all_files)
    print(f"Found {len(all_files)} aircraft files.")

    if sample_files is not None and sample_files < len(all_files):
        random.seed(seed)
        files = random.sample(all_files, sample_files)  # random, not first N
    else:
        files = all_files
    print(f"Processing {len(files)} files...")

    nacp_counts = Counter()
    version_counts = Counter()
    files_with_nacp = 0
    total_points = 0

    for path in files:
        data = load_trace(path)
        if data is None:
            continue

        has_nacp = False
        for _, _, _, _, nac_p, _, version in iter_points(data):
            total_points += 1
            nacp_counts[nac_p] += 1
            version_counts[version] += 1
            if nac_p is not None:
                has_nacp = True
        files_with_nacp += has_nacp

    # --- report ---
    known = sum(v for k, v in nacp_counts.items() if k is not None)
    print("\n=== SANITY CHECK ===")
    print(f"Files processed:       {len(files)}")
    print(f"Files with nac_p:      {files_with_nacp}")
    print(f"Total points:          {total_points:,}")
    print(f"Points with nac_p:     {known:,} ({known / max(total_points, 1):.1%})")
    print("ADS-B versions:", dict(sorted(version_counts.items(), key=lambda x: str(x[0]))))
    print("nac_p counts:", dict(sorted((k, v) for k, v in nacp_counts.items() if k is not None)))

    # --- histogram (percent of points with a known nac_p) ---
    values = list(range(12))
    freqs = [nacp_counts.get(v, 0) for v in values]
    pcts = [100 * f / known for f in freqs] if known else [0] * len(values)

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.bar(values, pcts, edgecolor="black", color="skyblue")

    for bar, pct, freq in zip(bars, pcts, freqs):
        if freq > 0:
            ax.annotate(
                f"{pct:.1f}%",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                ha="center", va="bottom", fontsize=9,
                xytext=(0, 2), textcoords="offset points",
            )

    ax.set_title(f"nac_p distribution ({DAY}, {len(files)} aircraft files, n={known:,} points)")
    ax.set_xlabel("nac_p")
    ax.set_ylabel("% of trace points")
    ax.set_xticks(values)
    ax.set_ylim(0, max(pcts, default=0) * 1.12 + 1)
    ax.grid(axis="y", alpha=0.5)
    fig.tight_layout()
    fig.savefig(f"nacp_hist_{DAY}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    run_sanity_checks()