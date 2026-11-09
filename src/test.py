import gzip
import os
import json
import glob
from collections import Counter
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
import random

#config data import
from src.config import DATA_DIR, DAY


def format_check():
    files = glob.glob(str(DATA_DIR / DAY / "traces" / "*" / "trace_full_*.json"))
    print(len(files), "aircraft files")

    with gzip.open(files[0], "rt") as fh:
        d = json.load(fh)

    print(d.keys())
    for p in d["trace"][:5]:
        print(p)


def run_adsb_sanity_checks(sample_files=1000):
    all_files = glob.glob(str(DATA_DIR / DAY / "traces" / "*" / "trace_full_*.json"))
    file_paths = all_files[:sample_files]

    total_files = len(file_paths)
    files_with_nacp_count = 0

    nacp_values = []
    versions = Counter()

    world_lats = []
    world_lons = []

    print(f"Found {len(all_files)} total files.")
    print(f"Processing a sample of {total_files} aircraft files...")

    for filepath in file_paths:
        try:
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Skipping {filepath} due to read error: {e}")
            continue

        if 'version' in data and data['version'] is not None:
            versions[f"top_level_v{data['version']}"] += 1

        trace = data.get('trace', [])
        file_has_nacp = False

        for point in trace:
            if len(point) < 3:
                continue

            lat, lon = point[1], point[2]

            # Collect ALL valid coordinates worldwide
            if lat is not None and lon is not None:
                world_lats.append(lat)
                world_lons.append(lon)

            # Extract nested dictionary (Index 8)
            if len(point) > 8 and isinstance(point[8], dict):
                info_dict = point[8]

                if 'nac_p' in info_dict:
                    nacp_values.append(info_dict['nac_p'])
                    file_has_nacp = True

                if 'version' in info_dict:
                    versions[f"trace_point_v{info_dict['version']}"] += 1

        if file_has_nacp:
            files_with_nacp_count += 1

    # --- PRINT SANITY CHECK REPORTS ---
    print("\n=== SANITY CHECK RESULTS ===")
    print(f"Sample aircraft files processed: {total_files}")
    print(f"Files containing ANY nac_p data: {files_with_nacp_count}")
    print(f"Total raw points collected globally: {len(world_lats)}")
    print("\nADS-B Versions encountered:")
    for version_type, count in versions.items():
        print(f"  - {version_type}: {count} occurrences")

    # --- PLOTTING ---
    if not nacp_values and not world_lats:
        print("\nNo valid data found.")
        return

    # 1. Plot nac_p Histogram using Matplotlib
    if nacp_values:
        plt.figure(figsize=(8, 6))
        plt.hist(nacp_values, bins=range(14), edgecolor='black', align='left', color='skyblue')
        plt.title("Histogram of nac_p Values\n(Expected: Peak around 8-11)")
        plt.xlabel("nac_p (Position Accuracy Category)")
        plt.ylabel("Frequency (Points)")
        plt.xticks(range(13))
        plt.grid(axis='y', alpha=0.5)
        plt.tight_layout()
        plt.show()

    # 2. Plot Global Map using Plotly Offline
    if world_lats:
        # Browser memory safety check
        max_points_to_plot = 500000
        if len(world_lats) > max_points_to_plot:
            print(f"\nDownsampling {len(world_lats)} points to {max_points_to_plot} for browser stability...")
            sampled_indices = random.sample(range(len(world_lats)), max_points_to_plot)
            plot_lats = [world_lats[i] for i in sampled_indices]
            plot_lons = [world_lons[i] for i in sampled_indices]
        else:
            plot_lats = world_lats
            plot_lons = world_lons

        df = pd.DataFrame({'Latitude': plot_lats, 'Longitude': plot_lons})

        # Use natural earth projection for a better global view
        fig = px.scatter_geo(
            df,
            lat="Latitude",
            lon="Longitude",
            title=f"Global ADS-B Coverage ({len(plot_lats):,} points)",
            projection="natural earth"
        )

        fig.update_geos(
            showcountries=True,
            showcoastlines=True,
            showland=True,
            showocean=True,
            landcolor="lightgray",
            oceancolor="lightblue",
            countrycolor="darkgray"
        )

        # Lower opacity even further for a global heatmap effect
        fig.update_traces(marker=dict(size=1.5, color='crimson', opacity=0.02))

        fig.write_html("global_map_offline.html", auto_open=True)

run_adsb_sanity_checks()